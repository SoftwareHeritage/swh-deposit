# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from abc import ABCMeta, abstractmethod
import datetime
import hashlib
import json
from typing import Any, Dict, Optional, Sequence, Tuple, Type, Union

import attr
from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import BaseAuthentication, BasicAuthentication
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from swh.deposit.api.checks import check_metadata
from swh.deposit.api.converters import convert_status_detail
from swh.deposit.models import Deposit
from swh.deposit.utils import compute_metadata_context
from swh.model import hashutil
from swh.model.identifiers import SWHID, ValidationError
from swh.model.model import (
    MetadataAuthority,
    MetadataAuthorityType,
    MetadataFetcher,
    RawExtrinsicMetadata,
)
from swh.scheduler.utils import create_oneshot_task_dict

from ..config import (
    ARCHIVE_KEY,
    ARCHIVE_TYPE,
    CONT_FILE_IRI,
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    DEPOSIT_STATUS_PARTIAL,
    EDIT_SE_IRI,
    EM_IRI,
    METADATA_KEY,
    METADATA_TYPE,
    RAW_METADATA_KEY,
    STATE_IRI,
    APIConfig,
)
from ..errors import (
    BAD_REQUEST,
    CHECKSUM_MISMATCH,
    ERROR_CONTENT,
    FORBIDDEN,
    MAX_UPLOAD_SIZE_EXCEEDED,
    MEDIATION_NOT_ALLOWED,
    METHOD_NOT_ALLOWED,
    NOT_FOUND,
    PARSING_ERROR,
    BadRequestError,
    ParserError,
    make_error_dict,
    make_error_response,
    make_error_response_from_dict,
    make_missing_slug_error,
)
from ..models import DepositClient, DepositCollection, DepositRequest
from ..parsers import parse_swh_reference, parse_xml

ACCEPT_PACKAGINGS = ["http://purl.org/net/sword/package/SimpleZip"]
ACCEPT_ARCHIVE_CONTENT_TYPES = ["application/zip", "application/x-tar"]


class AuthenticatedAPIView(APIView):
    """Mixin intended as a based API view to enforce the basic
       authentication check

    """

    authentication_classes: Sequence[Type[BaseAuthentication]] = (BasicAuthentication,)
    permission_classes: Sequence[Type[BasePermission]] = (IsAuthenticated,)


class APIBase(APIConfig, AuthenticatedAPIView, metaclass=ABCMeta):
    """Base deposit request class sharing multiple common behaviors.

    """

    def _read_headers(self, request: Request) -> Dict[str, Any]:
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

        swhid = meta.get("HTTP_X_CHECK_SWHID")

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
            "swhid": swhid,
        }

    def _compute_md5(self, filehandler) -> bytes:
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
        self,
        request: Request,
        deposit_id: Optional[int] = None,
        in_progress: bool = False,
        external_id: Optional[str] = None,
    ) -> Deposit:
        """Save/Update a deposit in db.

        Args:
            request: request data
            deposit_id: deposit identifier
            in_progress: deposit status
            external_id: external identifier to associate to the deposit

        Returns:
            The Deposit instance saved or updated.

        """
        complete_date: Optional[datetime.datetime] = None
        deposit_parent: Optional[Deposit] = None

        if in_progress is False:
            complete_date = timezone.now()
            status_type = DEPOSIT_STATUS_DEPOSITED
        else:
            status_type = DEPOSIT_STATUS_PARTIAL

        if not deposit_id:
            try:
                # find a deposit parent (same external id, status load to success)
                deposit_parent = (
                    Deposit.objects.filter(
                        external_id=external_id, status=DEPOSIT_STATUS_LOAD_SUCCESS
                    )
                    .order_by("-id")[0:1]
                    .get()
                )
            except Deposit.DoesNotExist:
                # then no parent for that deposit, deposit_parent already None
                pass

            deposit = Deposit(
                collection=self._collection,
                external_id=external_id or "",
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
                    retries_left=3,
                )
                check_task_id = scheduler.create_tasks([task])[0]["id"]
                deposit.check_task_id = check_task_id

        deposit.save()

        return deposit

    def _deposit_request_put(
        self,
        deposit: Deposit,
        deposit_request_data: Dict[str, Any],
        replace_metadata: bool = False,
        replace_archives: bool = False,
    ) -> DepositRequest:
        """Save a deposit request with metadata attached to a deposit.

        Args:
            deposit: The deposit concerned by the request
            deposit_request_data: The dictionary with at most 2 deposit
              request types (archive, metadata) to associate to the deposit
            replace_metadata: Flag defining if we add or update
              existing metadata to the deposit
            replace_archives: Flag defining if we add or update
              archives to existing deposit

        Returns:
            the DepositRequest object stored in the backend

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
            raw_metadata = deposit_request_data[RAW_METADATA_KEY]
            deposit_request = DepositRequest(
                type=METADATA_TYPE,
                deposit=deposit,
                metadata=metadata,
                raw_metadata=raw_metadata.decode("utf-8"),
            )
            deposit_request.save()

        assert deposit_request is not None
        return deposit_request

    def _delete_archives(self, collection_name: str, deposit_id: int) -> Dict:
        """Delete archive references from the deposit id.

        """
        try:
            deposit = Deposit.objects.get(pk=deposit_id)
        except Deposit.DoesNotExist:
            return make_error_dict(
                NOT_FOUND, f"The deposit {deposit_id} does not exist"
            )
        DepositRequest.objects.filter(deposit=deposit, type=ARCHIVE_TYPE).delete()

        return {}

    def _delete_deposit(self, collection_name: str, deposit_id: int) -> Dict:
        """Delete deposit reference.

        Args:
            collection_name: Client's collection
            deposit_id: The deposit to delete

        Returns
            Empty dict when ok.
            Dict with error key to describe the failure.

        """
        try:
            deposit = Deposit.objects.get(pk=deposit_id)
        except Deposit.DoesNotExist:
            return make_error_dict(
                NOT_FOUND, f"The deposit {deposit_id} does not exist"
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

    def _check_preconditions_on(
        self, filehandler, md5sum: str, content_length: Optional[int] = None
    ) -> Optional[Dict]:
        """Check preconditions on provided file are respected. That is the
           length and/or the md5sum hash match the file's content.

        Args:
            filehandler (InMemoryUploadedFile): The file to check
            md5sum: md5 hash expected from the file's content
            content_length: the expected length if provided.

        Returns:
            Either none if no error or a dictionary with a key error
            detailing the problem.

        """
        max_upload_size = self.config["max_upload_size"]
        if content_length:
            if content_length > max_upload_size:
                return make_error_dict(
                    MAX_UPLOAD_SIZE_EXCEEDED,
                    f"Upload size limit exceeded (max {max_upload_size} bytes)."
                    "Please consider sending the archive in multiple steps.",
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
                    f"The checksum sent {hashutil.hash_to_hex(md5sum)} and the actual "
                    f"checksum {hashutil.hash_to_hex(_md5sum)} does not match.",
                )

        return None

    def _binary_upload(
        self,
        request: Request,
        headers: Dict[str, Any],
        collection_name: str,
        deposit_id: Optional[int] = None,
        replace_metadata: bool = False,
        replace_archives: bool = False,
        check_slug_is_present: bool = False,
    ) -> Dict[str, Any]:
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
            check_slug_is_present: Check for the slug header if True and raise
              if not present

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
                "For archive deposit, the CONTENT_LENGTH header must be sent.",
            )

        content_disposition = headers["content-disposition"]
        if not content_disposition:
            return make_error_dict(
                BAD_REQUEST,
                "CONTENT_DISPOSITION header is mandatory",
                "For archive deposit, the CONTENT_DISPOSITION header must be sent.",
            )

        packaging = headers["packaging"]
        if packaging and packaging not in ACCEPT_PACKAGINGS:
            return make_error_dict(
                BAD_REQUEST,
                f"Only packaging {ACCEPT_PACKAGINGS} is supported",
                f"The packaging provided {packaging} is not supported",
            )

        filehandler = request.FILES["file"]

        precondition_status_response = self._check_preconditions_on(
            filehandler, headers["content-md5sum"], content_length
        )

        if precondition_status_response:
            return precondition_status_response

        slug = headers.get("slug")
        if check_slug_is_present and not slug:
            return make_missing_slug_error()

        # actual storage of data
        archive_metadata = filehandler
        deposit = self._deposit_put(
            request,
            deposit_id=deposit_id,
            in_progress=headers["in-progress"],
            external_id=slug,
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

    def _read_metadata(self, metadata_stream) -> Tuple[bytes, Dict[str, Any]]:
        """Given a metadata stream, reads the metadata and returns both the
           parsed and the raw metadata.

        """
        raw_metadata = metadata_stream.read()
        metadata = parse_xml(raw_metadata)
        return raw_metadata, metadata

    def _multipart_upload(
        self,
        request: Request,
        headers: Dict[str, Any],
        collection_name: str,
        deposit_id: Optional[int] = None,
        replace_metadata: bool = False,
        replace_archives: bool = False,
        check_slug_is_present: bool = False,
    ) -> Dict:
        """Multipart upload supported with exactly:
        - 1 archive (zip)
        - 1 atom entry

        Other than such a request, a 415 response is returned.

        Args:
            request (Request): the request holding information to parse
                and inject in db
            headers: request headers formatted
            collection_name: the associated client
            deposit_id: deposit identifier if provided
            replace_metadata: 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives: 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
              ones.
            check_slug_is_present: Check for the slug header if True and raise
              if not present

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
        slug = headers.get("slug")
        if check_slug_is_present and not slug:
            return make_missing_slug_error()

        content_types_present = set()

        data: Dict[str, Optional[Any]] = {
            "application/zip": None,  # expected either zip
            "application/x-tar": None,  # or x-tar
            "application/atom+xml": None,
        }
        for key, value in request.FILES.items():
            fh = value
            content_type = fh.content_type
            if content_type in content_types_present:
                return make_error_dict(
                    ERROR_CONTENT,
                    "Only 1 application/zip (or application/x-tar) archive "
                    "and 1 atom+xml entry is supported (as per sword2.0 "
                    "specification)",
                    "You provided more than 1 application/(zip|x-tar) "
                    "or more than 1 application/atom+xml content-disposition "
                    "header in the multipart deposit",
                )

            content_types_present.add(content_type)
            assert content_type is not None
            data[content_type] = fh

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
            external_id=slug,
        )
        deposit_request_data = {
            ARCHIVE_KEY: filehandler,
            METADATA_KEY: metadata,
            RAW_METADATA_KEY: raw_metadata,
        }
        self._deposit_request_put(
            deposit, deposit_request_data, replace_metadata, replace_archives
        )

        assert filehandler is not None
        return {
            "deposit_id": deposit.id,
            "deposit_date": deposit.reception_date,
            "archive": filehandler.name,
            "status": deposit.status,
        }

    def _store_metadata_deposit(
        self,
        deposit: Deposit,
        swhid_reference: Union[str, SWHID],
        metadata: Dict,
        raw_metadata: bytes,
        deposit_origin: Optional[str] = None,
    ) -> Tuple[Union[SWHID, str], Union[SWHID, str], Deposit, DepositRequest]:
        """When all user inputs pass the checks, this associates the raw_metadata to the
           swhid_reference in the raw extrinsic metadata storage. In case of any issues,
           a bad request response is returned to the user with the details.

            Checks:
            - metadata are technically parsable
            - metadata pass the functional checks
            - SWHID (if any) is technically valid

        Args:
            deposit: Deposit reference
            swhid_reference: The swhid or the origin to attach metadata information to
            metadata: Full dict of metadata to check for validity (parsed out of
              raw_metadata)
            raw_metadata: The actual raw metadata to send in the storage metadata
            deposit_origin: Optional deposit origin url to use if any (e.g. deposit
              update scenario provides one)

        Raises:
            BadRequestError in case of incorrect inputs from the deposit client
            (e.g. functionally invalid metadata, ...)

        Returns:
            Tuple of core swhid, swhid context, deposit and deposit request

        """
        metadata_ok, error_details = check_metadata(metadata)
        if not metadata_ok:
            assert error_details, "Details should be set when a failure occurs"
            raise BadRequestError(
                "Functional metadata checks failure",
                convert_status_detail(error_details),
            )

        metadata_authority = MetadataAuthority(
            type=MetadataAuthorityType.DEPOSIT_CLIENT,
            url=deposit.client.provider_url,
            metadata={"name": deposit.client.last_name},
        )

        metadata_fetcher = MetadataFetcher(
            name=self.tool["name"],
            version=self.tool["version"],
            metadata=self.tool["configuration"],
        )

        # replace metadata within the deposit backend
        deposit_request_data = {
            METADATA_KEY: metadata,
            RAW_METADATA_KEY: raw_metadata,
        }

        # actually add the metadata to the completed deposit
        deposit_request = self._deposit_request_put(deposit, deposit_request_data)

        object_type, metadata_context = compute_metadata_context(swhid_reference)
        if deposit_origin:  # metadata deposit update on completed deposit
            metadata_context["origin"] = deposit_origin

        swhid_core: Union[str, SWHID]
        if isinstance(swhid_reference, str):
            swhid_core = swhid_reference
        else:
            swhid_core = attr.evolve(swhid_reference, metadata={})

        # store that metadata to the metadata storage
        metadata_object = RawExtrinsicMetadata(
            type=object_type,
            target=swhid_core,  # core swhid or origin
            discovery_date=deposit_request.date,
            authority=metadata_authority,
            fetcher=metadata_fetcher,
            format="sword-v2-atom-codemeta",
            metadata=raw_metadata,
            **metadata_context,
        )

        # write to metadata storage
        self.storage_metadata.metadata_authority_add([metadata_authority])
        self.storage_metadata.metadata_fetcher_add([metadata_fetcher])
        self.storage_metadata.raw_extrinsic_metadata_add([metadata_object])

        return (swhid_core, swhid_reference, deposit, deposit_request)

    def _atom_entry(
        self,
        request: Request,
        headers: Dict[str, Any],
        collection_name: str,
        deposit_id: Optional[int] = None,
        replace_metadata: bool = False,
        replace_archives: bool = False,
        check_slug_is_present: bool = False,
    ) -> Dict[str, Any]:
        """Atom entry deposit.

        Args:
            request: the request holding information to parse
                and inject in db
            headers: request headers formatted
            collection_name: the associated client
            deposit_id: deposit identifier if provided
            replace_metadata: 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives: 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
              ones.
            check_slug_is_present: Check for the slug header if True and raise
              if not present

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

        # Determine if we are in the metadata-only deposit case
        try:
            swhid = parse_swh_reference(metadata)
        except ValidationError as e:
            return make_error_dict(PARSING_ERROR, "Invalid SWHID reference", str(e),)

        if swhid is not None:
            external_id = metadata.get("external_identifier", headers.get("slug"))
        else:
            slug = headers.get("slug")
            if check_slug_is_present and not slug:
                return make_missing_slug_error()

            external_id = metadata.get("external_identifier", slug)

        deposit = self._deposit_put(
            request,
            deposit_id=deposit_id,
            in_progress=headers["in-progress"],
            external_id=external_id,
        )

        if swhid is not None:
            try:
                swhid, swhid_ref, depo, depo_request = self._store_metadata_deposit(
                    deposit, swhid, metadata, raw_metadata
                )
            except BadRequestError as bad_request_error:
                return bad_request_error.to_dict()

            deposit.status = DEPOSIT_STATUS_LOAD_SUCCESS
            if isinstance(swhid_ref, SWHID):
                deposit.swhid = str(swhid)
                deposit.swhid_context = str(swhid_ref)
            deposit.complete_date = depo_request.date
            deposit.reception_date = depo_request.date
            deposit.save()

            return {
                "deposit_id": deposit.id,
                "deposit_date": depo_request.date,
                "status": deposit.status,
                "archive": None,
            }

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

    def _empty_post(
        self, request: Request, headers: Dict, collection_name: str, deposit_id: int
    ) -> Dict[str, Any]:
        """Empty post to finalize an empty deposit.

        Args:
            request: the request holding information to parse
                and inject in db
            headers: request headers formatted
            collection_name: the associated client
            deposit_id: deposit identifier

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

    def _make_iris(
        self, request: Request, collection_name: str, deposit_id: int
    ) -> Dict[str, Any]:
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

    def additional_checks(
        self,
        request: Request,
        headers: Dict[str, Any],
        collection_name: str,
        deposit_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Permit the child class to enrich additional checks.

        Returns:
            dict with 'error' detailing the problem.

        """
        return {}

    def checks(
        self, request: Request, collection_name: str, deposit_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            self._collection = DepositCollection.objects.get(name=collection_name)
        except DepositCollection.DoesNotExist:
            return make_error_dict(
                NOT_FOUND, f"Unknown collection name {collection_name}"
            )
        assert self._collection is not None

        username = request.user.username
        if username:  # unauthenticated request can have the username empty
            try:
                self._client: DepositClient = DepositClient.objects.get(  # type: ignore
                    username=username
                )
            except DepositClient.DoesNotExist:
                return make_error_dict(NOT_FOUND, f"Unknown client name {username}")

            collection_id = self._collection.id
            collections = self._client.collections
            assert collections is not None
            if collection_id not in collections:
                return make_error_dict(
                    FORBIDDEN,
                    f"Client {username} cannot access collection {collection_name}",
                )

        headers = self._read_headers(request)

        if deposit_id:
            try:
                deposit = Deposit.objects.get(pk=deposit_id)
            except Deposit.DoesNotExist:
                return make_error_dict(
                    NOT_FOUND, f"Deposit with id {deposit_id} does not exist"
                )

            assert deposit is not None
            checks = self.restrict_access(request, headers, deposit)
            if checks:
                return checks

        if headers["on-behalf-of"]:
            return make_error_dict(MEDIATION_NOT_ALLOWED, "Mediation is not supported.")

        checks = self.additional_checks(request, headers, collection_name, deposit_id)
        if "error" in checks:
            return checks

        return {"headers": headers}

    def restrict_access(
        self, request: Request, headers: Dict, deposit: Deposit
    ) -> Dict[str, Any]:
        """Allow modifications on deposit with status 'partial' only, reject the rest.

        """
        if request.method != "GET" and deposit.status != DEPOSIT_STATUS_PARTIAL:
            summary = "You can only act on deposit with status '%s'" % (
                DEPOSIT_STATUS_PARTIAL,
            )
            description = f"This deposit has status '{deposit.status}'"
            return make_error_dict(
                BAD_REQUEST, summary=summary, verbose_description=description
            )
        return {}

    def _basic_not_allowed_method(self, request: Request, method: str):
        return make_error_response(
            request,
            METHOD_NOT_ALLOWED,
            f"{method} method is not supported on this endpoint",
        )

    def get(
        self, request: Request, collection_name: str, deposit_id: int
    ) -> Union[HttpResponse, FileResponse]:
        return self._basic_not_allowed_method(request, "GET")

    def post(
        self, request: Request, collection_name: str, deposit_id: Optional[int] = None
    ) -> HttpResponse:
        return self._basic_not_allowed_method(request, "POST")

    def put(
        self, request: Request, collection_name: str, deposit_id: int
    ) -> HttpResponse:
        return self._basic_not_allowed_method(request, "PUT")

    def delete(
        self, request: Request, collection_name: str, deposit_id: Optional[int] = None
    ) -> HttpResponse:
        return self._basic_not_allowed_method(request, "DELETE")


class APIGet(APIBase, metaclass=ABCMeta):
    """Mixin for class to support GET method.

    """

    def get(
        self, request: Request, collection_name: str, deposit_id: int
    ) -> Union[HttpResponse, FileResponse]:
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

        status, content, content_type = r
        if content_type == "swh/generator":
            with content as path:
                return FileResponse(
                    open(path, "rb"), status=status, content_type="application/zip"
                )
        if content_type == "application/json":
            return HttpResponse(
                json.dumps(content), status=status, content_type=content_type
            )
        return HttpResponse(content, status=status, content_type=content_type)

    @abstractmethod
    def process_get(
        self, request: Request, collection_name: str, deposit_id: int
    ) -> Tuple[int, Any, str]:
        """Routine to deal with the deposit's get processing.

        Returns:
            Tuple status, stream of content, content-type

        """
        pass


class APIPost(APIBase, metaclass=ABCMeta):
    """Mixin for class to support POST method.

    """

    def post(
        self, request: Request, collection_name: str, deposit_id: Optional[int] = None
    ) -> HttpResponse:
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
        response._headers["location"] = "Location", data[_iri_key]  # type: ignore
        return response

    @abstractmethod
    def process_post(
        self,
        request,
        headers: Dict,
        collection_name: str,
        deposit_id: Optional[int] = None,
    ) -> Tuple[int, str, Dict]:
        """Routine to deal with the deposit's processing.

        Returns
            Tuple of:
            - response status code (200, 201, etc...)
            - key iri (EM_IRI, EDIT_SE_IRI, etc...)
            - dictionary of the processing result

        """
        pass


class APIPut(APIBase, metaclass=ABCMeta):
    """Mixin for class to support PUT method.

    """

    def put(
        self, request: Request, collection_name: str, deposit_id: int
    ) -> HttpResponse:
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
    def process_put(
        self, request: Request, headers: Dict, collection_name: str, deposit_id: int
    ) -> Dict[str, Any]:
        """Routine to deal with updating a deposit in some way.

        Returns
            dictionary of the processing result

        """
        pass


class APIDelete(APIBase, metaclass=ABCMeta):
    """Mixin for class to support DELETE method.

    """

    def delete(
        self, request: Request, collection_name: str, deposit_id: Optional[int] = None
    ) -> HttpResponse:
        """Endpoint to delete some deposit's resources (archives, deposit).

        Returns:
            204 response when no error during routine occurred.
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        checks = self.checks(request, collection_name, deposit_id)
        if "error" in checks:
            return make_error_response_from_dict(request, checks["error"])

        assert deposit_id is not None
        data = self.process_delete(request, collection_name, deposit_id)
        error = data.get("error")
        if error:
            return make_error_response_from_dict(request, error)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @abstractmethod
    def process_delete(
        self, request: Request, collection_name: str, deposit_id: int
    ) -> Dict:
        """Routine to delete a resource.

        This is mostly not allowed except for the
        EM_IRI (cf. .api.deposit_update.APIUpdateArchive)

        """
        return {}
