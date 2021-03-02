# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from rest_framework.request import Request

from swh.deposit.models import Deposit
from swh.model.identifiers import QualifiedSWHID

from ..config import DEPOSIT_STATUS_LOAD_SUCCESS
from ..errors import BAD_REQUEST, DepositError, ParserError
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
    ) -> None:
        """Relax restriction access to allow metadata update on deposit with status "done" when
        a swhid is provided.

        """
        if (
            request.method == "PUT"
            and headers.swhid is not None
            and deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS
        ):
            # Allow metadata update on deposit with status "done" when swhid provided
            return
        # otherwise, let the standard access restriction check occur
        super().restrict_access(request, headers, deposit)

    def process_put(
        self,
        request,
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit: Deposit,
    ) -> None:
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

        """  # noqa
        swhid = headers.swhid
        if swhid is None:
            if request.content_type.startswith("multipart/"):
                self._multipart_upload(
                    request,
                    headers,
                    collection_name,
                    deposit=deposit,
                    replace_archives=True,
                    replace_metadata=True,
                )
            else:
                # standard metadata update (replace all metadata already provided to the
                # deposit by the new ones)
                self._atom_entry(
                    request,
                    headers,
                    collection_name,
                    deposit=deposit,
                    replace_metadata=True,
                )
            return

        # Update metadata on a deposit already ingested
        # Write to the metadata storage (and the deposit backend)
        # no ingestion triggered

        assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS

        if swhid != deposit.swhid:
            raise DepositError(
                BAD_REQUEST,
                f"Mismatched provided SWHID {swhid} with deposit's {deposit.swhid}.",
                "The provided SWHID does not match the deposit to update. "
                "Please ensure you send the correct deposit SWHID.",
            )

        try:
            raw_metadata, metadata = self._read_metadata(request.data)
        except ParserError:
            raise DepositError(
                BAD_REQUEST,
                "Malformed xml metadata",
                "The xml received is malformed. "
                "Please ensure your metadata file is correctly formatted.",
            )

        if not metadata:
            raise DepositError(
                BAD_REQUEST,
                "Empty body request is not supported",
                "Atom entry deposit is supposed to send for metadata. "
                "If the body is empty, there is no metadata.",
            )

        _, deposit, deposit_request = self._store_metadata_deposit(
            deposit,
            QualifiedSWHID.from_string(swhid),
            metadata,
            raw_metadata,
            deposit.origin_url,
        )

    def process_delete(self, req, collection_name: str, deposit: Deposit) -> None:
        """Delete the container (deposit).

           source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_deleteconteiner  # noqa

        """
        self._delete_deposit(collection_name, deposit)
