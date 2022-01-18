# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from abc import ABCMeta, abstractmethod
import datetime
import hashlib
import json
from typing import Any, Dict, Optional, Sequence, Tuple, Type, Union
import uuid

import attr
from django.core.files.uploadedfile import UploadedFile
from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import BaseAuthentication, BasicAuthentication
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from swh.deposit.api.checks import check_metadata
from swh.deposit.api.converters import convert_status_detail
from swh.deposit.auth import HasDepositPermission, KeycloakBasicAuthentication
from swh.deposit.models import Deposit
from swh.deposit.utils import compute_metadata_context
from swh.model import hashutil
from swh.model.model import (
    MetadataAuthority,
    MetadataAuthorityType,
    Origin,
    RawExtrinsicMetadata,
)
from swh.model.swhids import (
    ExtendedObjectType,
    ExtendedSWHID,
    QualifiedSWHID,
    ValidationError,
)
from swh.scheduler.utils import create_oneshot_task_dict

from ..config import (
    ARCHIVE_KEY,
    ARCHIVE_TYPE,
    CONT_FILE_IRI,
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    DEPOSIT_STATUS_PARTIAL,
    EDIT_IRI,
    EM_IRI,
    METADATA_KEY,
    METADATA_TYPE,
    RAW_METADATA_KEY,
    SE_IRI,
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
    DepositError,
    ParserError,
)
from ..models import DepositClient, DepositCollection, DepositRequest
from ..parsers import parse_xml
from ..utils import extended_swhid_from_qualified, parse_swh_reference

ACCEPT_PACKAGINGS = ["http://purl.org/net/sword/package/SimpleZip"]
ACCEPT_ARCHIVE_CONTENT_TYPES = ["application/zip", "application/x-tar"]


@attr.s
class ParsedRequestHeaders:
    content_type = attr.ib(type=str)
    content_length = attr.ib(type=Optional[int])
    in_progress = attr.ib(type=bool)
    content_disposition = attr.ib(type=Optional[str])
    content_md5sum = attr.ib(type=Optional[bytes])
    packaging = attr.ib(type=Optional[str])
    slug = attr.ib(type=Optional[str])
    on_behalf_of = attr.ib(type=Optional[str])
    metadata_relevant = attr.ib(type=Optional[str])
    swhid = attr.ib(type=Optional[str])


@attr.s
class Receipt:
    """Data computed while handling the request body that will be served in the
    Deposit Receipt."""

    deposit_id = attr.ib(type=int)
    deposit_date = attr.ib(type=datetime.datetime)
    status = attr.ib(type=str)
    archive = attr.ib(type=Optional[str])


def _compute_md5(filehandler: UploadedFile) -> bytes:
    h = hashlib.md5()
    for chunk in filehandler:
        h.update(chunk)  # type: ignore
    return h.digest()


def get_deposit_by_id(
    deposit_id: int, collection_name: Optional[str] = None
) -> Deposit:
    """Gets an existing Deposit object if it exists, or raises `DepositError`.
    If `collection` is not None, also checks the deposit belongs to the collection."""
    try:
        deposit = Deposit.objects.get(pk=deposit_id)
    except Deposit.DoesNotExist:
        raise DepositError(NOT_FOUND, f"Deposit {deposit_id} does not exist")

    if collection_name and deposit.collection.name != collection_name:
        get_collection_by_name(collection_name)  # raises if does not exist

        raise DepositError(
            NOT_FOUND,
            f"Deposit {deposit_id} does not belong to collection {collection_name}",
        )

    return deposit


def get_collection_by_name(collection_name: str):
    """Gets an existing Deposit object if it exists, or raises `DepositError`."""
    try:
        collection = DepositCollection.objects.get(name=collection_name)
    except DepositCollection.DoesNotExist:
        raise DepositError(NOT_FOUND, f"Unknown collection name {collection_name}")

    assert collection is not None

    return collection


def guess_deposit_origin_url(deposit: Deposit):
    """Guesses an origin url for the given deposit."""
    external_id = deposit.external_id
    if not external_id:
        # The client provided neither an origin_url nor a slug. That's inconvenient,
        # but SWORD requires we support it. So let's generate a random slug.
        external_id = str(uuid.uuid4())
    return "%s/%s" % (deposit.client.provider_url.rstrip("/"), external_id)


def check_client_origin(client: DepositClient, origin_url: str):
    provider_url = client.provider_url.rstrip("/") + "/"
    if not origin_url.startswith(provider_url):
        raise DepositError(
            FORBIDDEN,
            f"Cannot create origin {origin_url}, it must start with {provider_url}",
        )


class APIBase(APIConfig, APIView, metaclass=ABCMeta):
    """Base deposit request class sharing multiple common behaviors.

    """

    _client: Optional[DepositClient] = None

    def __init__(self):
        super().__init__()
        auth_provider = self.config.get("authentication_provider")
        if auth_provider == "basic":
            self.authentication_classes: Sequence[Type[BaseAuthentication]] = (
                BasicAuthentication,
            )
            self.permission_classes: Sequence[Type[BasePermission]] = (IsAuthenticated,)
        elif auth_provider == "keycloak":
            self.authentication_classes: Sequence[Type[BaseAuthentication]] = (
                KeycloakBasicAuthentication,
            )
            self.permission_classes: Sequence[Type[BasePermission]] = (
                IsAuthenticated,
                HasDepositPermission,
            )
        else:
            raise ValueError(
                "Configuration key 'authentication_provider' should be provided with"
                f"either 'basic' or 'keycloak' value not {auth_provider!r}."
            )

    def _read_headers(self, request: Request) -> ParsedRequestHeaders:
        """Read and unify the necessary headers from the request (those are
           not stored in the same location or not properly formatted).

        Args:
            request: Input request

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

        content_length = meta.get("CONTENT_LENGTH")
        if content_length and isinstance(content_length, str):
            content_length = int(content_length)

        # final deposit if not provided
        in_progress = meta.get("HTTP_IN_PROGRESS", False)
        if isinstance(in_progress, str):
            in_progress = in_progress.lower() == "true"

        content_md5sum = meta.get("HTTP_CONTENT_MD5")
        if content_md5sum:
            content_md5sum = bytes.fromhex(content_md5sum)

        return ParsedRequestHeaders(
            content_type=request.content_type,
            content_length=content_length,
            in_progress=in_progress,
            content_disposition=meta.get("HTTP_CONTENT_DISPOSITION"),
            content_md5sum=content_md5sum,
            packaging=meta.get("HTTP_PACKAGING"),
            slug=meta.get("HTTP_SLUG"),
            on_behalf_of=meta.get("HTTP_ON_BEHALF_OF"),
            metadata_relevant=meta.get("HTTP_METADATA_RELEVANT"),
            swhid=meta.get("HTTP_X_CHECK_SWHID"),
        )

    def _deposit_put(self, deposit: Deposit, in_progress: bool = False) -> None:
        """Save/Update a deposit in db.

        Args:
            deposit: deposit being updated/created
            in_progress: deposit status
        """
        if in_progress is False:
            self._complete_deposit(deposit)
        else:
            deposit.status = DEPOSIT_STATUS_PARTIAL
            deposit.save()

    def _complete_deposit(self, deposit: Deposit) -> None:
        """Marks the deposit as 'deposited', then schedule a check task if configured
        to do so."""
        deposit.complete_date = timezone.now()
        deposit.status = DEPOSIT_STATUS_DEPOSITED
        deposit.save()

        if not deposit.origin_url:
            deposit.origin_url = guess_deposit_origin_url(deposit)

        if self.config["checks"]:
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

    def _delete_archives(self, collection_name: str, deposit: Deposit) -> Dict:
        """Delete archive references from the deposit id.

        """
        DepositRequest.objects.filter(deposit=deposit, type=ARCHIVE_TYPE).delete()

        return {}

    def _delete_deposit(self, collection_name: str, deposit: Deposit) -> Dict:
        """Delete deposit reference.

        Args:
            collection_name: Client's collection
            deposit: The deposit to delete

        Returns
            Empty dict when ok.
            Dict with error key to describe the failure.

        """
        if deposit.collection.name != collection_name:
            summary = "Cannot delete a deposit from another collection"
            description = "Deposit %s does not belong to the collection %s" % (
                deposit.id,
                collection_name,
            )
            raise DepositError(
                BAD_REQUEST, summary=summary, verbose_description=description
            )

        DepositRequest.objects.filter(deposit=deposit).delete()
        deposit.delete()

        return {}

    def _check_file_length(
        self, filehandler: UploadedFile, content_length: Optional[int] = None,
    ) -> None:
        """Check the filehandler passed as argument has exactly the
        expected content_length

        Args:
            filehandler: The file to check
            content_length: the expected length if provided.

        Raises:
            DepositError if the actual length does not match
        """
        max_upload_size = self.config["max_upload_size"]
        if content_length:
            length = filehandler.size
            if length != content_length:
                raise DepositError(status.HTTP_412_PRECONDITION_FAILED, "Wrong length")

        if filehandler.size > max_upload_size:
            raise DepositError(
                MAX_UPLOAD_SIZE_EXCEEDED,
                f"Upload size limit exceeded (max {max_upload_size} bytes)."
                "Please consider sending the archive in multiple steps.",
            )

    def _check_file_md5sum(
        self, filehandler: UploadedFile, md5sum: Optional[bytes],
    ) -> None:
        """Check the filehandler passed as argument has the expected md5sum

        Args:
            filehandler: The file to check
            md5sum: md5 hash expected from the file's content

        Raises:
            DepositError if the md5sum does not match

        """
        if md5sum:
            _md5sum = _compute_md5(filehandler)
            if _md5sum != md5sum:
                raise DepositError(
                    CHECKSUM_MISMATCH,
                    "Wrong md5 hash",
                    f"The checksum sent {hashutil.hash_to_hex(md5sum)} and the actual "
                    f"checksum {hashutil.hash_to_hex(_md5sum)} does not match.",
                )

    def _binary_upload(
        self,
        request: Request,
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit: Deposit,
        replace_metadata: bool = False,
        replace_archives: bool = False,
    ) -> Receipt:
        """Binary upload routine.

        Other than such a request, a 415 response is returned.

        Args:
            request: the request holding information to parse
                and inject in db
            headers: parsed request headers
            collection_name: the associated client
            deposit: deposit to be updated
            replace_metadata: 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives: 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
              ones.

        Raises:
            - 400 (bad request) if the request is not providing an external
              identifier
            - 413 (request entity too large) if the length of the
              archive exceeds the max size configured
            - 412 (precondition failed) if the length or md5 hash provided
              mismatch the reality of the archive
            - 415 (unsupported media type) if a wrong media type is provided

        """
        content_length = headers.content_length
        if not content_length:
            raise DepositError(
                BAD_REQUEST,
                "CONTENT_LENGTH header is mandatory",
                "For archive deposit, the CONTENT_LENGTH header must be sent.",
            )

        content_disposition = headers.content_disposition
        if not content_disposition:
            raise DepositError(
                BAD_REQUEST,
                "CONTENT_DISPOSITION header is mandatory",
                "For archive deposit, the CONTENT_DISPOSITION header must be sent.",
            )

        packaging = headers.packaging
        if packaging and packaging not in ACCEPT_PACKAGINGS:
            raise DepositError(
                BAD_REQUEST,
                f"Only packaging {ACCEPT_PACKAGINGS} is supported",
                f"The packaging provided {packaging} is not supported",
            )

        filehandler = request.FILES["file"]
        assert isinstance(filehandler, UploadedFile), filehandler

        self._check_file_length(filehandler, content_length)
        self._check_file_md5sum(filehandler, headers.content_md5sum)

        # actual storage of data
        archive_metadata = filehandler
        self._deposit_put(
            deposit=deposit, in_progress=headers.in_progress,
        )
        self._deposit_request_put(
            deposit,
            {ARCHIVE_KEY: archive_metadata},
            replace_metadata=replace_metadata,
            replace_archives=replace_archives,
        )

        return Receipt(
            deposit_id=deposit.id,
            deposit_date=deposit.reception_date,
            status=deposit.status,
            archive=filehandler.name,
        )

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
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit: Deposit,
        replace_metadata: bool = False,
        replace_archives: bool = False,
    ) -> Receipt:
        """Multipart upload supported with exactly:
        - 1 archive (zip)
        - 1 atom entry

        Other than such a request, a 415 response is returned.

        Args:
            request: the request holding information to parse
                and inject in db
            headers: parsed request headers
            collection_name: the associated client
            deposit: deposit to be updated
            replace_metadata: 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives: 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
              ones.

        Raises:
            - 400 (bad request) if the request is not providing an external
              identifier
            - 412 (precondition failed) if the potentially md5 hash provided
              mismatch the reality of the archive
            - 413 (request entity too large) if the length of the
              archive exceeds the max size configured
            - 415 (unsupported media type) if a wrong media type is provided

        """
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
                raise DepositError(
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
            raise DepositError(
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

        assert isinstance(filehandler, UploadedFile), filehandler

        self._check_file_length(filehandler)
        self._check_file_md5sum(filehandler, headers.content_md5sum)

        try:
            raw_metadata, metadata = self._read_metadata(data["application/atom+xml"])
        except ParserError:
            raise DepositError(
                PARSING_ERROR,
                "Malformed xml metadata",
                "The xml received is malformed. "
                "Please ensure your metadata file is correctly formatted.",
            )

        self._set_deposit_origin_from_metadata(deposit, metadata, headers)

        # actual storage of data
        self._deposit_put(
            deposit=deposit, in_progress=headers.in_progress,
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
        return Receipt(
            deposit_id=deposit.id,
            deposit_date=deposit.reception_date,
            archive=filehandler.name,
            status=deposit.status,
        )

    def _store_metadata_deposit(
        self,
        deposit: Deposit,
        swhid_reference: Union[str, QualifiedSWHID],
        metadata: Dict,
        raw_metadata: bytes,
        deposit_origin: Optional[str] = None,
    ) -> Tuple[ExtendedSWHID, Deposit, DepositRequest]:
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
            DepositError in case of incorrect inputs from the deposit client
            (e.g. functionally invalid metadata, ...)

        Returns:
            Tuple of target swhid, deposit, and deposit request

        """
        metadata_ok, error_details = check_metadata(metadata)
        if not metadata_ok:
            assert error_details, "Details should be set when a failure occurs"
            raise DepositError(
                BAD_REQUEST,
                "Functional metadata checks failure",
                convert_status_detail(error_details),
            )

        metadata_authority = MetadataAuthority(
            type=MetadataAuthorityType.DEPOSIT_CLIENT, url=deposit.client.provider_url,
        )

        metadata_fetcher = self.swh_deposit_fetcher()

        # replace metadata within the deposit backend
        deposit_request_data = {
            METADATA_KEY: metadata,
            RAW_METADATA_KEY: raw_metadata,
        }

        # actually add the metadata to the completed deposit
        deposit_request = self._deposit_request_put(deposit, deposit_request_data)

        target_swhid: ExtendedSWHID  # origin URL or CoreSWHID
        if isinstance(swhid_reference, str):
            target_swhid = Origin(swhid_reference).swhid()
            metadata_context = {}
        else:
            metadata_context = compute_metadata_context(swhid_reference)
            if deposit_origin:  # metadata deposit update on completed deposit
                metadata_context["origin"] = deposit_origin

            target_swhid = extended_swhid_from_qualified(swhid_reference)

        self._check_swhid_in_archive(target_swhid)

        # metadata deposited by the client
        metadata_object = RawExtrinsicMetadata(
            target=target_swhid,  # core swhid or origin
            discovery_date=deposit_request.date,
            authority=metadata_authority,
            fetcher=metadata_fetcher,
            format="sword-v2-atom-codemeta",
            metadata=raw_metadata,
            **metadata_context,
        )

        # metadata on the metadata object
        swh_deposit_authority = self.swh_deposit_authority()
        swh_deposit_fetcher = self.swh_deposit_fetcher()
        metametadata_object = RawExtrinsicMetadata(
            target=metadata_object.swhid(),
            discovery_date=deposit_request.date,
            authority=swh_deposit_authority,
            fetcher=swh_deposit_fetcher,
            format="xml-deposit-info",
            metadata=render_to_string(
                "deposit/deposit_info.xml", context={"deposit": deposit}
            ).encode(),
        )

        # write to metadata storage
        self.storage_metadata.metadata_authority_add(
            [metadata_authority, swh_deposit_authority]
        )
        self.storage_metadata.metadata_fetcher_add(
            [metadata_fetcher, swh_deposit_fetcher]
        )
        self.storage_metadata.raw_extrinsic_metadata_add(
            [metadata_object, metametadata_object]
        )

        return (target_swhid, deposit, deposit_request)

    def _check_swhid_in_archive(self, target_swhid: ExtendedSWHID) -> None:
        """Check the target object already exists in the archive,
        and raises a BAD_REQUEST if it does not."""
        if target_swhid.object_type in (ExtendedObjectType.CONTENT,):
            if list(
                self.storage.content_missing_per_sha1_git([target_swhid.object_id])
            ):
                raise DepositError(
                    BAD_REQUEST,
                    f"Cannot load metadata on {target_swhid}, this content "
                    f"object does not exist in the archive (yet?).",
                )
        elif target_swhid.object_type in (
            ExtendedObjectType.DIRECTORY,
            ExtendedObjectType.REVISION,
            ExtendedObjectType.RELEASE,
            ExtendedObjectType.SNAPSHOT,
        ):
            target_type_name = target_swhid.object_type.name.lower()
            method = getattr(self.storage, target_type_name + "_missing")
            if list(method([target_swhid.object_id])):
                raise DepositError(
                    BAD_REQUEST,
                    f"Cannot load metadata on {target_swhid}, this {target_type_name} "
                    f"object does not exist in the archive (yet?).",
                )
        elif target_swhid.object_type in (ExtendedObjectType.ORIGIN,):
            if None in list(self.storage.origin_get_by_sha1([target_swhid.object_id])):
                raise DepositError(
                    BAD_REQUEST,
                    "Cannot load metadata on origin, it is not (yet?) known to the "
                    "archive.",
                )
        else:
            # This should not happen, because target_swhid is generated from either
            # a core swhid or an origin URL.
            # Let's just check it again so the "switch" is exhaustive.
            raise ValueError(
                f"_check_swhid_in_archive expected core SWHID or origin SWHID, "
                f"but got {target_swhid}."
            )

    def _atom_entry(
        self,
        request: Request,
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit: Deposit,
        replace_metadata: bool = False,
        replace_archives: bool = False,
    ) -> Receipt:
        """Atom entry deposit.

        Args:
            request: the request holding information to parse
                and inject in db
            headers: parsed request headers
            collection_name: the associated client
            deposit: deposit to be updated
            replace_metadata: 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives: 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
              ones.

        Raises:
            - 400 (bad request) if the request is not providing an external
              identifier
            - 400 (bad request) if the request's body is empty
            - 415 (unsupported media type) if a wrong media type is provided

        """
        metadata_stream = request.data
        empty_atom_entry_summary = "Empty body request is not supported."
        empty_atom_entry_desc = (
            "Atom entry request is about non-empty metadata deposit."
        )
        if not metadata_stream:
            raise DepositError(
                BAD_REQUEST, empty_atom_entry_summary, empty_atom_entry_desc
            )

        try:
            raw_metadata, metadata = self._read_metadata(metadata_stream)
        except ParserError:
            raise DepositError(
                BAD_REQUEST,
                "Malformed xml metadata",
                "The xml received is malformed. "
                "Please ensure your metadata file is correctly formatted.",
            )

        if metadata is None:
            raise DepositError(
                BAD_REQUEST, empty_atom_entry_summary, empty_atom_entry_desc
            )

        self._set_deposit_origin_from_metadata(deposit, metadata, headers)

        # Determine if we are in the metadata-only deposit case
        try:
            swhid_ref = parse_swh_reference(metadata)
        except ValidationError as e:
            raise DepositError(
                PARSING_ERROR, "Invalid SWHID reference", str(e),
            )

        if swhid_ref is not None and (
            deposit.origin_url or deposit.parent or deposit.external_id
        ):
            raise DepositError(
                BAD_REQUEST,
                "<swh:reference> is for metadata-only deposits and "
                "<swh:create_origin> / <swh:add_to_origin> / Slug are for "
                "code deposits, only one may be used on a given deposit.",
            )

        if swhid_ref is not None:
            deposit.save()  # We need a deposit id
            target_swhid, depo, depo_request = self._store_metadata_deposit(
                deposit, swhid_ref, metadata, raw_metadata
            )

            deposit.status = DEPOSIT_STATUS_LOAD_SUCCESS
            if isinstance(swhid_ref, QualifiedSWHID):
                deposit.swhid = str(extended_swhid_from_qualified(swhid_ref))
                deposit.swhid_context = str(swhid_ref)
            deposit.complete_date = depo_request.date
            deposit.reception_date = depo_request.date
            deposit.save()

            return Receipt(
                deposit_id=deposit.id,
                deposit_date=depo_request.date,
                status=deposit.status,
                archive=None,
            )

        self._deposit_put(
            deposit=deposit, in_progress=headers.in_progress,
        )

        self._deposit_request_put(
            deposit,
            {METADATA_KEY: metadata, RAW_METADATA_KEY: raw_metadata},
            replace_metadata,
            replace_archives,
        )

        return Receipt(
            deposit_id=deposit.id,
            deposit_date=deposit.reception_date,
            status=deposit.status,
            archive=None,
        )

    def _set_deposit_origin_from_metadata(self, deposit, metadata, headers):
        create_origin = metadata.get("swh:deposit", {}).get("swh:create_origin")
        add_to_origin = metadata.get("swh:deposit", {}).get("swh:add_to_origin")

        if create_origin and add_to_origin:
            raise DepositError(
                BAD_REQUEST,
                "<swh:create_origin> and <swh:add_to_origin> are mutually exclusive, "
                "as they respectively create a new origin and add to an existing "
                "origin.",
            )

        if create_origin:
            origin_url = create_origin["swh:origin"]["@url"]
            check_client_origin(deposit.client, origin_url)
            deposit.origin_url = origin_url

        if add_to_origin:
            origin_url = add_to_origin["swh:origin"]["@url"]
            check_client_origin(deposit.client, origin_url)
            deposit.parent = (
                Deposit.objects.filter(
                    client=deposit.client,
                    origin_url=origin_url,
                    status=DEPOSIT_STATUS_LOAD_SUCCESS,
                )
                .order_by("-id")[0:1]
                .get()
            )
            deposit.origin_url = origin_url

        if "atom:external_identifier" in metadata:
            # Deprecated tag.
            # When clients stopped using it, this should raise an error
            # unconditionally

            if deposit.origin_url:
                raise DepositError(
                    BAD_REQUEST,
                    "<external_identifier> is deprecated, you should only use "
                    "<swh:create_origin> and <swh:add_to_origin> from now on.",
                )

            if headers.slug and metadata["atom:external_identifier"] != headers.slug:
                raise DepositError(
                    BAD_REQUEST,
                    "The <external_identifier> tag and Slug header are deprecated, "
                    "<swh:create_origin> or <swh:add_to_origin> "
                    "should be used instead.",
                )

    def _empty_post(
        self,
        request: Request,
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit: Deposit,
    ) -> Receipt:
        """Empty post to finalize a deposit.

        Args:
            request: the request holding information to parse
                and inject in db
            headers: parsed request headers
            collection_name: the associated client
            deposit: deposit to be finalized
        """
        self._complete_deposit(deposit)

        assert deposit.complete_date is not None

        return Receipt(
            deposit_id=deposit.id,
            deposit_date=deposit.complete_date,
            status=deposit.status,
            archive=None,
        )

    def additional_checks(
        self,
        request: Request,
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit: Optional[Deposit],
    ) -> Dict[str, Any]:
        """Permit the child class to enrich additional checks.

        Returns:
            dict with 'error' detailing the problem.

        """
        return {}

    def get_client(self, request) -> DepositClient:
        # This class depends on AuthenticatedAPIView, so request.user.username
        # is always set
        username = request.user.username
        assert username is not None

        if self._client is None:
            try:
                self._client = DepositClient.objects.get(  # type: ignore
                    username=username
                )
            except DepositClient.DoesNotExist:
                raise DepositError(NOT_FOUND, f"Unknown client name {username}")

        assert self._client.username == username

        return self._client

    def checks(
        self, request: Request, collection_name: str, deposit: Optional[Deposit] = None
    ) -> ParsedRequestHeaders:
        if deposit is None:
            collection = get_collection_by_name(collection_name)
        else:
            assert collection_name == deposit.collection.name
            collection = deposit.collection

        client = self.get_client(request)
        collection_id = collection.id
        collections = client.collections
        assert collections is not None
        if collection_id not in collections:
            raise DepositError(
                FORBIDDEN,
                f"Client {client.username} cannot access collection {collection_name}",
            )

        headers = self._read_headers(request)

        if deposit is not None:
            self.restrict_access(request, headers, deposit)

        if headers.on_behalf_of:
            raise DepositError(MEDIATION_NOT_ALLOWED, "Mediation is not supported.")

        self.additional_checks(request, headers, collection_name, deposit)

        return headers

    def restrict_access(
        self, request: Request, headers: ParsedRequestHeaders, deposit: Deposit
    ) -> None:
        """Allow modifications on deposit with status 'partial' only, reject the rest.

        """
        if request.method != "GET" and deposit.status != DEPOSIT_STATUS_PARTIAL:
            summary = "You can only act on deposit with status '%s'" % (
                DEPOSIT_STATUS_PARTIAL,
            )
            description = f"This deposit has status '{deposit.status}'"
            raise DepositError(
                BAD_REQUEST, summary=summary, verbose_description=description
            )

    def _basic_not_allowed_method(self, request: Request, method: str):
        raise DepositError(
            METHOD_NOT_ALLOWED, f"{method} method is not supported on this endpoint",
        )

    def get(
        self, request: Request, *args, **kwargs
    ) -> Union[HttpResponse, FileResponse]:
        return self._basic_not_allowed_method(request, "GET")

    def post(self, request: Request, *args, **kwargs) -> HttpResponse:
        return self._basic_not_allowed_method(request, "POST")

    def put(self, request: Request, *args, **kwargs) -> HttpResponse:
        return self._basic_not_allowed_method(request, "PUT")

    def delete(self, request: Request, *args, **kwargs) -> HttpResponse:
        return self._basic_not_allowed_method(request, "DELETE")


class APIGet(APIBase, metaclass=ABCMeta):
    """Mixin for class to support GET method.

    """

    def get(  # type: ignore
        self, request: Request, collection_name: str, deposit_id: int
    ) -> Union[HttpResponse, FileResponse]:
        """Endpoint to create/add resources to deposit.

        Returns:
            200 response when no error during routine occurred
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        deposit = get_deposit_by_id(deposit_id, collection_name)
        self.checks(request, collection_name, deposit)

        r = self.process_get(request, collection_name, deposit)

        status, content, content_type = r
        if content_type == "swh/generator":
            with content as path:
                return FileResponse(
                    open(path, "rb"), status=status, content_type="application/tar"
                )
        if content_type == "application/json":
            return HttpResponse(
                json.dumps(content), status=status, content_type=content_type
            )
        return HttpResponse(content, status=status, content_type=content_type)

    @abstractmethod
    def process_get(
        self, request: Request, collection_name: str, deposit: Deposit
    ) -> Tuple[int, Any, str]:
        """Routine to deal with the deposit's get processing.

        Returns:
            Tuple status, stream of content, content-type

        """
        pass


class APIPost(APIBase, metaclass=ABCMeta):
    """Mixin for class to support POST method.

    """

    def post(  # type: ignore
        self, request: Request, collection_name: str, deposit_id: Optional[int] = None
    ) -> HttpResponse:
        """Endpoint to create/add resources to deposit.

        Returns:
            204 response when no error during routine occurred.
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        if deposit_id is None:
            deposit = None
        else:
            deposit = get_deposit_by_id(deposit_id, collection_name)
        headers = self.checks(request, collection_name, deposit)

        status, iri_key, receipt = self.process_post(
            request, headers, collection_name, deposit
        )

        return self._make_deposit_receipt(
            request, collection_name, status, iri_key, receipt,
        )

    def _make_deposit_receipt(
        self,
        request,
        collection_name: str,
        status: int,
        iri_key: str,
        receipt: Receipt,
    ) -> HttpResponse:
        """Returns an HttpResponse with a SWORD Deposit receipt as content."""

        # Build the IRIs in the receipt
        args = [collection_name, receipt.deposit_id]
        iris = {
            iri: request.build_absolute_uri(reverse(iri, args=args))
            for iri in [EM_IRI, EDIT_IRI, CONT_FILE_IRI, SE_IRI, STATE_IRI]
        }

        context = {
            **attr.asdict(receipt),
            **iris,
            "packagings": ACCEPT_PACKAGINGS,
        }

        response = render(
            request,
            "deposit/deposit_receipt.xml",
            context=context,
            content_type="application/xml",
            status=status,
        )
        response["Location"] = iris[iri_key]
        return response

    @abstractmethod
    def process_post(
        self,
        request,
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit: Optional[Deposit] = None,
    ) -> Tuple[int, str, Receipt]:
        """Routine to deal with the deposit's processing.

        Returns
            Tuple of:
            - response status code (200, 201, etc...)
            - key iri (EM_IRI, EDIT_IRI, etc...)
            - Receipt

        """
        pass


class APIPut(APIBase, metaclass=ABCMeta):
    """Mixin for class to support PUT method.

    """

    def put(  # type: ignore
        self, request: Request, collection_name: str, deposit_id: int
    ) -> HttpResponse:
        """Endpoint to update deposit resources.

        Returns:
            204 response when no error during routine occurred.
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        if deposit_id is None:
            deposit = None
        else:
            deposit = get_deposit_by_id(deposit_id, collection_name)
        headers = self.checks(request, collection_name, deposit)
        self.process_put(request, headers, collection_name, deposit)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @abstractmethod
    def process_put(
        self,
        request: Request,
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit: Deposit,
    ) -> None:
        """Routine to deal with updating a deposit in some way.

        Returns
            dictionary of the processing result

        """
        pass


class APIDelete(APIBase, metaclass=ABCMeta):
    """Mixin for class to support DELETE method.

    """

    def delete(  # type: ignore
        self, request: Request, collection_name: str, deposit_id: Optional[int] = None
    ) -> HttpResponse:
        """Endpoint to delete some deposit's resources (archives, deposit).

        Returns:
            204 response when no error during routine occurred.
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        assert deposit_id is not None
        deposit = get_deposit_by_id(deposit_id, collection_name)
        self.checks(request, collection_name, deposit)
        self.process_delete(request, collection_name, deposit)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @abstractmethod
    def process_delete(
        self, request: Request, collection_name: str, deposit: Deposit
    ) -> None:
        """Routine to delete a resource.

        This is mostly not allowed except for the
        EM_IRI (cf. .api.deposit_update.APIUpdateArchive)

        """
        pass
