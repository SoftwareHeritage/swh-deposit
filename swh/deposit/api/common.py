# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from typing import Sequence, Type

from abc import ABCMeta, abstractmethod
from django.urls import reverse
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import BaseAuthentication, BasicAuthentication
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.views import APIView

from swh.model import hashutil
from swh.scheduler.utils import create_oneshot_task_dict

from ..config import (
    SWHDefaultConfig,
    EDIT_SE_IRI,
    EM_IRI,
    CONT_FILE_IRI,
    ARCHIVE_KEY,
    METADATA_KEY,
    RAW_METADATA_KEY,
    STATE_IRI,
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_PARTIAL,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    ARCHIVE_TYPE,
    METADATA_TYPE,
)
from ..errors import (
    MAX_UPLOAD_SIZE_EXCEEDED,
    BAD_REQUEST,
    ERROR_CONTENT,
    CHECKSUM_MISMATCH,
    make_error_dict,
    MEDIATION_NOT_ALLOWED,
    make_error_response_from_dict,
    FORBIDDEN,
    NOT_FOUND,
    make_error_response,
    METHOD_NOT_ALLOWED,
    ParserError,
    PARSING_ERROR,
)
from ..models import Deposit, DepositRequest, DepositCollection, DepositClient
from ..parsers import parse_xml


ACCEPT_PACKAGINGS = ["http://purl.org/net/sword/package/SimpleZip"]
ACCEPT_ARCHIVE_CONTENT_TYPES = ["application/zip", "application/x-tar"]


class SWHAPIView(APIView):
    """Mixin intended as a based API view to enforce the basic
       authentication check

    """

    authentication_classes: Sequence[Type[BaseAuthentication]] = (BasicAuthentication,)
    permission_classes: Sequence[Type[BasePermission]] = (IsAuthenticated,)


class SWHBaseDeposit(SWHDefaultConfig, SWHAPIView, metaclass=ABCMeta):
    """Base deposit request class sharing multiple common behaviors.

    """

    def _read_headers(self, request):
        """Read and unify the necessary headers from the request (those are
           not stored in the same location or not properly formatted).

        Args:
            request (Request): Input request

        Returns:
            Dictionary with the following keys (some associated values may be
              None):
                - content-type
                - content-length
                - in-progress
                - content-disposition
                - packaging
                - slug
                - on-behalf-of

        """
        meta = request._request.META
        content_type = request.content_type
        content_length = meta.get("CONTENT_LENGTH")
        if content_length and isinstance(content_length, str):
            content_length = int(content_length)

        # final deposit if not provided
        in_progress = meta.get("HTTP_IN_PROGRESS", False)
        content_disposition = meta.get("HTTP_CONTENT_DISPOSITION")
        if isinstance(in_progress, str):
            in_progress = in_progress.lower() == "true"

        content_md5sum = meta.get("HTTP_CONTENT_MD5")
        if content_md5sum:
            content_md5sum = bytes.fromhex(content_md5sum)

        packaging = meta.get("HTTP_PACKAGING")
        slug = meta.get("HTTP_SLUG")
        on_behalf_of = meta.get("HTTP_ON_BEHALF_OF")
        metadata_relevant = meta.get("HTTP_METADATA_RELEVANT")

        return {
            "content-type": content_type,
            "content-length": content_length,
            "in-progress": in_progress,
            "content-disposition": content_disposition,
            "content-md5sum": content_md5sum,
            "packaging": packaging,
            "slug": slug,
            "on-behalf-of": on_behalf_of,
            "metadata-relevant": metadata_relevant,
        }

    def _compute_md5(self, filehandler):
        """Compute uploaded file's md5 sum.

        Args:
            filehandler (InMemoryUploadedFile): the file to compute the md5
                hash

        Returns:
            the md5 checksum (str)

        """
        h = hashlib.md5()
        for chunk in filehandler:
            h.update(chunk)
        return h.digest()

    def _deposit_put(
        self, request, deposit_id=None, in_progress=False, external_id=None
    ):
        """Save/Update a deposit in db.

        Args:
            deposit_id (int): deposit identifier
            in_progress (dict): The deposit's status
            external_id (str): The external identifier to associate to
              the deposit

        Returns:
            The Deposit instance saved or updated.

        """
        if in_progress is False:
            complete_date = timezone.now()
            status_type = DEPOSIT_STATUS_DEPOSITED
        else:
            complete_date = None
            status_type = DEPOSIT_STATUS_PARTIAL

        if not deposit_id:
            try:
                # find a deposit parent (same external id, status load
                # to success)
                deposit_parent = (
                    Deposit.objects.filter(
                        external_id=external_id, status=DEPOSIT_STATUS_LOAD_SUCCESS
                    )
                    .order_by("-id")[0:1]
                    .get()
                )  # noqa
            except Deposit.DoesNotExist:
                deposit_parent = None

            deposit = Deposit(
                collection=self._collection,
                external_id=external_id,
                complete_date=complete_date,
                status=status_type,
                client=self._client,
                parent=deposit_parent,
            )
        else:
            deposit = Deposit.objects.get(pk=deposit_id)

            # update metadata
            deposit.complete_date = complete_date
            deposit.status = status_type

        if self.config["checks"]:
            deposit.save()  # needed to have a deposit id
            scheduler = self.scheduler
            if deposit.status == DEPOSIT_STATUS_DEPOSITED and not deposit.check_task_id:
                task = create_oneshot_task_dict(
                    "check-deposit",
                    collection=deposit.collection.name,
                    deposit_id=deposit.id,
                )
                check_task_id = scheduler.create_tasks([task])[0]["id"]
                deposit.check_task_id = check_task_id

        deposit.save()

        return deposit

    def _deposit_request_put(
        self,
        deposit,
        deposit_request_data,
        replace_metadata=False,
        replace_archives=False,
    ):
        """Save a deposit request with metadata attached to a deposit.

        Args:
            deposit (Deposit): The deposit concerned by the request
            deposit_request_data (dict): The dictionary with at most 2 deposit
            request types (archive, metadata) to associate to the deposit
            replace_metadata (bool): Flag defining if we add or update
              existing metadata to the deposit
            replace_archives (bool): Flag defining if we add or update
              archives to existing deposit

        Returns:
            None

        """
        if replace_metadata:
            DepositRequest.objects.filter(deposit=deposit, type=METADATA_TYPE).delete()

        if replace_archives:
            DepositRequest.objects.filter(deposit=deposit, type=ARCHIVE_TYPE).delete()

        deposit_request = None

        archive_file = deposit_request_data.get(ARCHIVE_KEY)
        if archive_file:
            deposit_request = DepositRequest(
                type=ARCHIVE_TYPE, deposit=deposit, archive=archive_file
            )
            deposit_request.save()

        metadata = deposit_request_data.get(METADATA_KEY)
        if metadata:
            raw_metadata = deposit_request_data.get(RAW_METADATA_KEY)
            deposit_request = DepositRequest(
                type=METADATA_TYPE,
                deposit=deposit,
                metadata=metadata,
                raw_metadata=raw_metadata.decode("utf-8"),
            )
            deposit_request.save()

        assert deposit_request is not None

    def _delete_archives(self, collection_name, deposit_id):
        """Delete archives reference from the deposit id.

        """
        try:
            deposit = Deposit.objects.get(pk=deposit_id)
        except Deposit.DoesNotExist:
            return make_error_dict(
                NOT_FOUND, "The deposit %s does not exist" % deposit_id
            )
        DepositRequest.objects.filter(deposit=deposit, type=ARCHIVE_TYPE).delete()

        return {}

    def _delete_deposit(self, collection_name, deposit_id):
        """Delete deposit reference.

        Args:
            collection_name (str): Client's name
            deposit_id (id): The deposit to delete

        Returns
            Empty dict when ok.
            Dict with error key to describe the failure.

        """
        try:
            deposit = Deposit.objects.get(pk=deposit_id)
        except Deposit.DoesNotExist:
            return make_error_dict(
                NOT_FOUND, "The deposit %s does not exist" % deposit_id
            )

        if deposit.collection.name != collection_name:
            summary = "Cannot delete a deposit from another collection"
            description = "Deposit %s does not belong to the collection %s" % (
                deposit_id,
                collection_name,
            )
            return make_error_dict(
                BAD_REQUEST, summary=summary, verbose_description=description
            )

        DepositRequest.objects.filter(deposit=deposit).delete()
        deposit.delete()

        return {}

    def _check_preconditions_on(self, filehandler, md5sum, content_length=None):
        """Check preconditions on provided file are respected. That is the
           length and/or the md5sum hash match the file's content.

        Args:
            filehandler (InMemoryUploadedFile): The file to check
            md5sum (hex str): md5 hash expected from the file's content
            content_length (int): the expected length if provided.

        Returns:
            Either none if no error or a dictionary with a key error
            detailing the problem.

        """
        if content_length:
            if content_length > self.config["max_upload_size"]:
                return make_error_dict(
                    MAX_UPLOAD_SIZE_EXCEEDED,
                    "Upload size limit exceeded (max %s bytes)."
                    % self.config["max_upload_size"],
                    "Please consider sending the archive in " "multiple steps.",
                )

            length = filehandler.size
            if length != content_length:
                return make_error_dict(
                    status.HTTP_412_PRECONDITION_FAILED, "Wrong length"
                )

        if md5sum:
            _md5sum = self._compute_md5(filehandler)
            if _md5sum != md5sum:
                return make_error_dict(
                    CHECKSUM_MISMATCH,
                    "Wrong md5 hash",
                    "The checksum sent %s and the actual checksum "
                    "%s does not match."
                    % (hashutil.hash_to_hex(md5sum), hashutil.hash_to_hex(_md5sum)),
                )

        return None

    def _binary_upload(
        self,
        request,
        headers,
        collection_name,
        deposit_id=None,
        replace_metadata=False,
        replace_archives=False,
    ):
        """Binary upload routine.

        Other than such a request, a 415 response is returned.

        Args:
            request (Request): the request holding information to parse
                and inject in db
            headers (dict): request headers formatted
            collection_name (str): the associated client
            deposit_id (id): deposit identifier if provided
            replace_metadata (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
              ones.

        Returns:
            In the optimal case a dict with the following keys:
                - deposit_id (int): Deposit identifier
                - deposit_date (date): Deposit date
                - archive: None (no archive is provided here)

            Otherwise, a dictionary with the key error and the
            associated failures, either:

            - 400 (bad request) if the request is not providing an external
              identifier
            - 413 (request entity too large) if the length of the
              archive exceeds the max size configured
            - 412 (precondition failed) if the length or md5 hash provided
              mismatch the reality of the archive
            - 415 (unsupported media type) if a wrong media type is provided

        """
        content_length = headers["content-length"]
        if not content_length:
            return make_error_dict(
                BAD_REQUEST,
                "CONTENT_LENGTH header is mandatory",
                "For archive deposit, the " "CONTENT_LENGTH header must be sent.",
            )

        content_disposition = headers["content-disposition"]
        if not content_disposition:
            return make_error_dict(
                BAD_REQUEST,
                "CONTENT_DISPOSITION header is mandatory",
                "For archive deposit, the " "CONTENT_DISPOSITION header must be sent.",
            )

        packaging = headers["packaging"]
        if packaging and packaging not in ACCEPT_PACKAGINGS:
            return make_error_dict(
                BAD_REQUEST,
                "Only packaging %s is supported" % ACCEPT_PACKAGINGS,
                "The packaging provided %s is not supported" % packaging,
            )

        filehandler = request.FILES["file"]

        precondition_status_response = self._check_preconditions_on(
            filehandler, headers["content-md5sum"], content_length
        )

        if precondition_status_response:
            return precondition_status_response

        external_id = headers["slug"]

        # actual storage of data
        archive_metadata = filehandler
        deposit = self._deposit_put(
            request,
            deposit_id=deposit_id,
            in_progress=headers["in-progress"],
            external_id=external_id,
        )
        self._deposit_request_put(
            deposit,
            {ARCHIVE_KEY: archive_metadata},
            replace_metadata=replace_metadata,
            replace_archives=replace_archives,
        )

        return {
            "deposit_id": deposit.id,
            "deposit_date": deposit.reception_date,
            "status": deposit.status,
            "archive": filehandler.name,
        }

    def _read_metadata(self, metadata_stream):
        """Given a metadata stream, reads the metadata and returns both the
           parsed and the raw metadata.

        """
        raw_metadata = metadata_stream.read()
        metadata = parse_xml(raw_metadata)
        return raw_metadata, metadata

    def _multipart_upload(
        self,
        request,
        headers,
        collection_name,
        deposit_id=None,
        replace_metadata=False,
        replace_archives=False,
    ):
        """Multipart upload supported with exactly:
        - 1 archive (zip)
        - 1 atom entry

        Other than such a request, a 415 response is returned.

        Args:
            request (Request): the request holding information to parse
                and inject in db
            headers (dict): request headers formatted
            collection_name (str): the associated client
            deposit_id (id): deposit identifier if provided
            replace_metadata (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
              ones.

        Returns:
            In the optimal case a dict with the following keys:
                - deposit_id (int): Deposit identifier
                - deposit_date (date): Deposit date
                - archive: None (no archive is provided here)

            Otherwise, a dictionary with the key error and the
            associated failures, either:

            - 400 (bad request) if the request is not providing an external
              identifier
            - 412 (precondition failed) if the potentially md5 hash provided
              mismatch the reality of the archive
            - 413 (request entity too large) if the length of the
              archive exceeds the max size configured
            - 415 (unsupported media type) if a wrong media type is provided

        """
        external_id = headers["slug"]

        content_types_present = set()

        data = {
            "application/zip": None,  # expected either zip
            "application/x-tar": None,  # or x-tar
            "application/atom+xml": None,
        }
        for key, value in request.FILES.items():
            fh = value
            if fh.content_type in content_types_present:
                return make_error_dict(
                    ERROR_CONTENT,
                    "Only 1 application/zip (or application/x-tar) archive "
                    "and 1 atom+xml entry is supported (as per sword2.0 "
                    "specification)",
                    "You provided more than 1 application/(zip|x-tar) "
                    "or more than 1 application/atom+xml content-disposition "
                    "header in the multipart deposit",
                )

            content_types_present.add(fh.content_type)
            data[fh.content_type] = fh

        if len(content_types_present) != 2:
            return make_error_dict(
                ERROR_CONTENT,
                "You must provide both 1 application/zip (or "
                "application/x-tar) and 1 atom+xml entry for multipart "
                "deposit",
                "You need to provide only 1 application/(zip|x-tar) "
                "and 1 application/atom+xml content-disposition header "
                "in the multipart deposit",
            )

        filehandler = data["application/zip"]
        if not filehandler:
            filehandler = data["application/x-tar"]

        precondition_status_response = self._check_preconditions_on(
            filehandler, headers["content-md5sum"]
        )

        if precondition_status_response:
            return precondition_status_response

        try:
            raw_metadata, metadata = self._read_metadata(data["application/atom+xml"])
        except ParserError:
            return make_error_dict(
                PARSING_ERROR,
                "Malformed xml metadata",
                "The xml received is malformed. "
                "Please ensure your metadata file is correctly formatted.",
            )

        # actual storage of data
        deposit = self._deposit_put(
            request,
            deposit_id=deposit_id,
            in_progress=headers["in-progress"],
            external_id=external_id,
        )
        deposit_request_data = {
            ARCHIVE_KEY: filehandler,
            METADATA_KEY: metadata,
            RAW_METADATA_KEY: raw_metadata,
        }
        self._deposit_request_put(
            deposit, deposit_request_data, replace_metadata, replace_archives
        )

        return {
            "deposit_id": deposit.id,
            "deposit_date": deposit.reception_date,
            "archive": filehandler.name,
            "status": deposit.status,
        }

    def _atom_entry(
        self,
        request,
        headers,
        collection_name,
        deposit_id=None,
        replace_metadata=False,
        replace_archives=False,
    ):
        """Atom entry deposit.

        Args:
            request (Request): the request holding information to parse
                and inject in db
            headers (dict): request headers formatted
            collection_name (str): the associated client
            deposit_id (id): deposit identifier if provided
            replace_metadata (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
              ones.

        Returns:
            In the optimal case a dict with the following keys:

                - deposit_id: deposit id associated to the deposit
                - deposit_date: date of the deposit
                - archive: None (no archive is provided here)

            Otherwise, a dictionary with the key error and the
            associated failures, either:

            - 400 (bad request) if the request is not providing an external
              identifier
            - 400 (bad request) if the request's body is empty
            - 415 (unsupported media type) if a wrong media type is provided

        """
        try:
            raw_metadata, metadata = self._read_metadata(request.data)
        except ParserError:
            return make_error_dict(
                BAD_REQUEST,
                "Malformed xml metadata",
                "The xml received is malformed. "
                "Please ensure your metadata file is correctly formatted.",
            )

        if not metadata:
            return make_error_dict(
                BAD_REQUEST,
                "Empty body request is not supported",
                "Atom entry deposit is supposed to send for metadata. "
                "If the body is empty, there is no metadata.",
            )

        external_id = metadata.get("external_identifier", headers["slug"])

        deposit = self._deposit_put(
            request,
            deposit_id=deposit_id,
            in_progress=headers["in-progress"],
            external_id=external_id,
        )

        self._deposit_request_put(
            deposit,
            {METADATA_KEY: metadata, RAW_METADATA_KEY: raw_metadata},
            replace_metadata,
            replace_archives,
        )

        return {
            "deposit_id": deposit.id,
            "deposit_date": deposit.reception_date,
            "archive": None,
            "status": deposit.status,
        }

    def _empty_post(self, request, headers, collection_name, deposit_id):
        """Empty post to finalize an empty deposit.

        Args:
            request (Request): the request holding information to parse
                and inject in db
            headers (dict): request headers formatted
            collection_name (str): the associated client
            deposit_id (id): deposit identifier

        Returns:
            Dictionary of result with the deposit's id, the date
            it was completed and no archive.

        """
        deposit = Deposit.objects.get(pk=deposit_id)
        deposit.complete_date = timezone.now()
        deposit.status = DEPOSIT_STATUS_DEPOSITED
        deposit.save()

        return {
            "deposit_id": deposit_id,
            "deposit_date": deposit.complete_date,
            "status": deposit.status,
            "archive": None,
        }

    def _make_iris(self, request, collection_name, deposit_id):
        """Define the IRI endpoints

        Args:
            request (Request): The initial request
            collection_name (str): client/collection's name
            deposit_id (id): Deposit identifier

        Returns:
            Dictionary of keys with the iris' urls.

        """
        args = [collection_name, deposit_id]
        return {
            iri: request.build_absolute_uri(reverse(iri, args=args))
            for iri in [EM_IRI, EDIT_SE_IRI, CONT_FILE_IRI, STATE_IRI]
        }

    def additional_checks(self, request, headers, collection_name, deposit_id=None):
        """Permit the child class to enrich additional checks.

        Returns:
            dict with 'error' detailing the problem.

        """
        return {}

    def checks(self, request, collection_name, deposit_id=None):
        try:
            self._collection = DepositCollection.objects.get(name=collection_name)
        except DepositCollection.DoesNotExist:
            return make_error_dict(
                NOT_FOUND, "Unknown collection name %s" % collection_name
            )

        username = request.user.username
        if username:  # unauthenticated request can have the username empty
            try:
                self._client = DepositClient.objects.get(username=username)
            except DepositClient.DoesNotExist:
                return make_error_dict(NOT_FOUND, "Unknown client name %s" % username)

            if self._collection.id not in self._client.collections:
                return make_error_dict(
                    FORBIDDEN,
                    "Client %s cannot access collection %s"
                    % (username, collection_name),
                )

        if deposit_id:
            try:
                deposit = Deposit.objects.get(pk=deposit_id)
            except Deposit.DoesNotExist:
                return make_error_dict(
                    NOT_FOUND, "Deposit with id %s does not exist" % deposit_id
                )

            checks = self.restrict_access(request, deposit)
            if checks:
                return checks

        headers = self._read_headers(request)
        if headers["on-behalf-of"]:
            return make_error_dict(MEDIATION_NOT_ALLOWED, "Mediation is not supported.")

        checks = self.additional_checks(request, headers, collection_name, deposit_id)
        if "error" in checks:
            return checks

        return {"headers": headers}

    def restrict_access(self, request, deposit=None):
        if deposit:
            if request.method != "GET" and deposit.status != DEPOSIT_STATUS_PARTIAL:
                summary = "You can only act on deposit with status '%s'" % (
                    DEPOSIT_STATUS_PARTIAL,
                )
                description = "This deposit has status '%s'" % deposit.status
                return make_error_dict(
                    BAD_REQUEST, summary=summary, verbose_description=description
                )

    def _basic_not_allowed_method(self, request, method):
        return make_error_response(
            request,
            METHOD_NOT_ALLOWED,
            "%s method is not supported on this endpoint" % method,
        )

    def get(self, request, *args, **kwargs):
        return self._basic_not_allowed_method(request, "GET")

    def post(self, request, *args, **kwargs):
        return self._basic_not_allowed_method(request, "POST")

    def put(self, request, *args, **kwargs):
        return self._basic_not_allowed_method(request, "PUT")

    def delete(self, request, *args, **kwargs):
        return self._basic_not_allowed_method(request, "DELETE")


class SWHGetDepositAPI(SWHBaseDeposit, metaclass=ABCMeta):
    """Mixin for class to support GET method.

    """

    def get(self, request, collection_name, deposit_id, format=None):
        """Endpoint to create/add resources to deposit.

        Returns:
            200 response when no error during routine occurred
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        checks = self.checks(request, collection_name, deposit_id)
        if "error" in checks:
            return make_error_response_from_dict(request, checks["error"])

        r = self.process_get(request, collection_name, deposit_id)

        if isinstance(r, tuple):
            status, content, content_type = r
            return HttpResponse(content, status=status, content_type=content_type)

        return r

    @abstractmethod
    def process_get(self, request, collection_name, deposit_id):
        """Routine to deal with the deposit's get processing.

        Returns:
            Tuple status, stream of content, content-type

        """
        pass


class SWHPostDepositAPI(SWHBaseDeposit, metaclass=ABCMeta):
    """Mixin for class to support DELETE method.

    """

    def post(self, request, collection_name, deposit_id=None, format=None):
        """Endpoint to create/add resources to deposit.

        Returns:
            204 response when no error during routine occurred.
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        checks = self.checks(request, collection_name, deposit_id)
        if "error" in checks:
            return make_error_response_from_dict(request, checks["error"])

        headers = checks["headers"]
        _status, _iri_key, data = self.process_post(
            request, headers, collection_name, deposit_id
        )

        error = data.get("error")
        if error:
            return make_error_response_from_dict(request, error)

        data["packagings"] = ACCEPT_PACKAGINGS
        iris = self._make_iris(request, collection_name, data["deposit_id"])
        data.update(iris)
        response = render(
            request,
            "deposit/deposit_receipt.xml",
            context=data,
            content_type="application/xml",
            status=_status,
        )
        response._headers["location"] = "Location", data[_iri_key]
        return response

    @abstractmethod
    def process_post(self, request, headers, collection_name, deposit_id=None):
        """Routine to deal with the deposit's processing.

        Returns
            Tuple of:
            - response status code (200, 201, etc...)
            - key iri (EM_IRI, EDIT_SE_IRI, etc...)
            - dictionary of the processing result

        """
        pass


class SWHPutDepositAPI(SWHBaseDeposit, metaclass=ABCMeta):
    """Mixin for class to support PUT method.

    """

    def put(self, request, collection_name, deposit_id, format=None):
        """Endpoint to update deposit resources.

        Returns:
            204 response when no error during routine occurred.
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        checks = self.checks(request, collection_name, deposit_id)
        if "error" in checks:
            return make_error_response_from_dict(request, checks["error"])

        headers = checks["headers"]
        data = self.process_put(request, headers, collection_name, deposit_id)

        error = data.get("error")
        if error:
            return make_error_response_from_dict(request, error)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @abstractmethod
    def process_put(self, request, headers, collection_name, deposit_id):
        """Routine to deal with updating a deposit in some way.

        Returns
            dictionary of the processing result

        """
        pass


class SWHDeleteDepositAPI(SWHBaseDeposit, metaclass=ABCMeta):
    """Mixin for class to support DELETE method.

    """

    def delete(self, request, collection_name, deposit_id):
        """Endpoint to delete some deposit's resources (archives, deposit).

        Returns:
            204 response when no error during routine occurred.
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        checks = self.checks(request, collection_name, deposit_id)
        if "error" in checks:
            return make_error_response_from_dict(request, checks["error"])

        data = self.process_delete(request, collection_name, deposit_id)
        error = data.get("error")
        if error:
            return make_error_response_from_dict(request, error)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @abstractmethod
    def process_delete(self, request, collection_name, deposit_id):
        """Routine to delete a resource.

        This is mostly not allowed except for the
        EM_IRI (cf. .api.deposit_update.SWHUpdateArchiveDeposit)

        """
        pass
