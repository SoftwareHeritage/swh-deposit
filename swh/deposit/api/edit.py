# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict

from rest_framework.request import Request

from swh.deposit.models import Deposit
from swh.model.identifiers import parse_swhid

from ..config import DEPOSIT_STATUS_LOAD_SUCCESS
from ..errors import BAD_REQUEST, BadRequestError, ParserError, make_error_dict
from ..parsers import SWHAtomEntryParser, SWHMultiPartParser
from .common import APIDelete, APIPut, ParsedRequestHeaders


class EditAPI(APIPut, APIDelete):
    """Deposit request class defining api endpoints for sword deposit.

       What's known as 'Edit-IRI' in the sword specification.

       HTTP verbs supported: PUT, DELETE

    """

    parser_classes = (SWHMultiPartParser, SWHAtomEntryParser)

    def restrict_access(
        self, request: Request, headers: ParsedRequestHeaders, deposit: Deposit
    ) -> Dict[str, Any]:
        """Relax restriction access to allow metadata update on deposit with status "done" when
        a swhid is provided.

        """
        if (
            request.method == "PUT"
            and headers.swhid is not None
            and deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS
        ):
            # Allow metadata update on deposit with status "done" when swhid provided
            return {}
        # otherwise, let the standard access restriction check occur
        return super().restrict_access(request, headers, deposit)

    def process_put(
        self,
        request,
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit_id: int,
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
        swhid = headers.swhid
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

    def process_delete(self, req, collection_name: str, deposit_id: int) -> Dict:
        """Delete the container (deposit).

           source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_deleteconteiner  # noqa

        """
        return self._delete_deposit(collection_name, deposit_id)