# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict, Optional, Tuple

from rest_framework import status
from rest_framework.request import Request

from swh.deposit.models import Deposit
from swh.model.identifiers import parse_swhid

from ..config import CONT_FILE_IRI, DEPOSIT_STATUS_LOAD_SUCCESS, EDIT_SE_IRI, EM_IRI
from ..errors import BAD_REQUEST, BadRequestError, ParserError, make_error_dict
from ..parsers import (
    SWHAtomEntryParser,
    SWHFileUploadTarParser,
    SWHFileUploadZipParser,
    SWHMultiPartParser,
)
from .common import ACCEPT_ARCHIVE_CONTENT_TYPES, APIDelete, APIPost, APIPut


class APIUpdateArchive(APIPost, APIPut, APIDelete):
    """Deposit request class defining api endpoints for sword deposit.

       What's known as 'EM IRI' in the sword specification.

       HTTP verbs supported: PUT, POST, DELETE

    """

    parser_classes = (
        SWHFileUploadZipParser,
        SWHFileUploadTarParser,
    )

    def process_put(
        self, req, headers, collection_name: str, deposit_id: int
    ) -> Dict[str, Any]:
        """Replace existing content for the existing deposit.

           source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_editingcontent_binary  # noqa

        Returns:
            204 No content

        """
        if req.content_type not in ACCEPT_ARCHIVE_CONTENT_TYPES:
            msg = "Packaging format supported is restricted to %s" % (
                ", ".join(ACCEPT_ARCHIVE_CONTENT_TYPES)
            )
            return make_error_dict(BAD_REQUEST, msg)

        return self._binary_upload(
            req, headers, collection_name, deposit_id=deposit_id, replace_archives=True
        )

    def process_post(
        self, req, headers: Dict, collection_name: str, deposit_id: Optional[int] = None
    ) -> Tuple[int, str, Dict]:
        """Add new content to the existing deposit.

           source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_addingcontent_mediaresource  # noqa

        Returns:
            201 Created
            Headers: Location: [Cont-File-IRI]

            Body: [optional Deposit Receipt]

        """
        if req.content_type not in ACCEPT_ARCHIVE_CONTENT_TYPES:
            msg = "Packaging format supported is restricted to %s" % (
                ", ".join(ACCEPT_ARCHIVE_CONTENT_TYPES)
            )
            unused = 0
            return unused, "unused", make_error_dict(BAD_REQUEST, msg)

        return (
            status.HTTP_201_CREATED,
            CONT_FILE_IRI,
            self._binary_upload(req, headers, collection_name, deposit_id),
        )

    def process_delete(self, req, collection_name: str, deposit_id: int) -> Dict:
        """Delete content (archives) from existing deposit.

           source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_deletingcontent  # noqa

        Returns:
            204 Created

        """
        return self._delete_archives(collection_name, deposit_id)


class APIUpdateMetadata(APIPost, APIPut, APIDelete):
    """Deposit request class defining api endpoints for sword deposit.

       What's known as 'Edit IRI' (and SE IRI) in the sword specification.

       HTTP verbs supported: POST (SE IRI), PUT (Edit IRI), DELETE

    """

    parser_classes = (SWHMultiPartParser, SWHAtomEntryParser)

    def restrict_access(
        self, request: Request, headers: Dict, deposit: Deposit
    ) -> Dict[str, Any]:
        """Relax restriction access to allow metadata update on deposit with status "done" when
        a swhid is provided.

        """
        if (
            request.method == "PUT"
            and headers["swhid"] is not None
            and deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS
        ):
            # Allow metadata update on deposit with status "done" when swhid provided
            return {}
        # otherwise, let the standard access restriction check occur
        return super().restrict_access(request, headers, deposit)

    def process_put(
        self, request, headers: Dict, collection_name: str, deposit_id: int
    ) -> Dict[str, Any]:
        """This allows the following scenarios:

        - multipart: replace all the deposit (status partial) metadata and archive
          with the provided ones.
        - atom: replace all the deposit (status partial) metadata with the
          provided ones.
        - with swhid, atom: Add new metatada to deposit (status done) with provided ones
          and push such metadata to the metadata storage directly.

           source:
           - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_editingcontent_metadata
           - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_editingcontent_multipart

        Raises:
            400 if any of the following occur:
            - the swhid provided and the deposit swhid do not match
            - the provided metadata xml file is malformed
            - the provided xml atom entry is empty
            - the provided swhid does not exist in the archive

        Returns:
            204 No content

        """  # noqa
        swhid = headers.get("swhid")
        if swhid is None:
            if request.content_type.startswith("multipart/"):
                return self._multipart_upload(
                    request,
                    headers,
                    collection_name,
                    deposit_id=deposit_id,
                    replace_archives=True,
                    replace_metadata=True,
                )
            # standard metadata update (replace all metadata already provided to the
            # deposit by the new ones)
            return self._atom_entry(
                request,
                headers,
                collection_name,
                deposit_id=deposit_id,
                replace_metadata=True,
            )

        # Update metadata on a deposit already ingested
        # Write to the metadata storage (and the deposit backend)
        # no ingestion triggered

        deposit = Deposit.objects.get(pk=deposit_id)
        assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS

        if swhid != deposit.swhid:
            return make_error_dict(
                BAD_REQUEST,
                f"Mismatched provided SWHID {swhid} with deposit's {deposit.swhid}.",
                "The provided SWHID does not match the deposit to update. "
                "Please ensure you send the correct deposit SWHID.",
            )

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

        try:
            _, _, deposit, deposit_request = self._store_metadata_deposit(
                deposit, parse_swhid(swhid), metadata, raw_metadata, deposit.origin_url,
            )
        except BadRequestError as bad_request_error:
            return bad_request_error.to_dict()

        return {
            "deposit_id": deposit.id,
            "deposit_date": deposit_request.date,
            "status": deposit.status,
            "archive": None,
        }

    def process_post(
        self,
        request,
        headers: Dict,
        collection_name: str,
        deposit_id: Optional[int] = None,
    ) -> Tuple[int, str, Dict]:
        """Add new metadata/archive to existing deposit.

        This allows the following scenarios to occur:

        - multipart: Add new metadata and archive to a deposit in status partial with
          the provided ones.

        - empty atom: Allows to finalize a deposit in status partial (transition to
          deposited).

           source:
           - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_addingcontent_metadata
           - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_addingcontent_multipart
           - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#continueddeposit_complete

        Returns:
            In optimal case for a multipart and atom-entry update, a
            201 Created response. The body response will hold a
            deposit. And the response headers will contain an entry
            'Location' with the EM-IRI.

            For the empty post case, this returns a 200.

        """  # noqa
        assert deposit_id is not None
        if request.content_type.startswith("multipart/"):
            data = self._multipart_upload(
                request, headers, collection_name, deposit_id=deposit_id
            )
            return (status.HTTP_201_CREATED, EM_IRI, data)

        content_length = headers["content-length"] or 0
        if content_length == 0 and headers["in-progress"] is False:
            # check for final empty post
            data = self._empty_post(request, headers, collection_name, deposit_id)
            return (status.HTTP_200_OK, EDIT_SE_IRI, data)

        data = self._atom_entry(
            request, headers, collection_name, deposit_id=deposit_id
        )
        return (status.HTTP_201_CREATED, EM_IRI, data)

    def process_delete(self, req, collection_name: str, deposit_id: int) -> Dict:
        """Delete the container (deposit).

           source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_deleteconteiner  # noqa

        """
        return self._delete_deposit(collection_name, deposit_id)
