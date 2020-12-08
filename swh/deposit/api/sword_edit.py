# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Optional, Tuple

from rest_framework import status

from swh.storage import get_storage
from swh.storage.interface import StorageInterface

from ..config import EDIT_IRI, EM_IRI
from ..models import Deposit
from ..parsers import SWHAtomEntryParser, SWHMultiPartParser
from .common import APIPost, ParsedRequestHeaders, Receipt


class SwordEditAPI(APIPost):
    """Deposit request class defining api endpoints for sword deposit.

       What's known as 'SE-IRI' in the sword specification.

       HTTP verbs supported: POST

    """

    parser_classes = (SWHMultiPartParser, SWHAtomEntryParser)

    def __init__(self):
        super().__init__()
        self.storage_metadata: StorageInterface = get_storage(
            **self.config["storage_metadata"]
        )

    def process_post(
        self,
        request,
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit: Optional[Deposit] = None,
    ) -> Tuple[int, str, Receipt]:
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
        assert deposit is not None
        if request.content_type.startswith("multipart/"):
            receipt = self._multipart_upload(
                request, headers, collection_name, deposit=deposit
            )
            return (status.HTTP_201_CREATED, EM_IRI, receipt)

        content_length = headers.content_length or 0
        if content_length == 0 and headers.in_progress is False:
            # check for final empty post
            receipt = self._empty_post(request, headers, collection_name, deposit)
            return (status.HTTP_200_OK, EDIT_IRI, receipt)

        receipt = self._atom_entry(request, headers, collection_name, deposit=deposit)
        return (status.HTTP_201_CREATED, EM_IRI, receipt)
