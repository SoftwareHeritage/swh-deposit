# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict, Optional, Tuple

from rest_framework import status

from ..config import CONT_FILE_IRI
from ..errors import BAD_REQUEST, DepositError
from ..parsers import SWHFileUploadTarParser, SWHFileUploadZipParser
from .common import (
    ACCEPT_ARCHIVE_CONTENT_TYPES,
    APIDelete,
    APIPost,
    APIPut,
    ParsedRequestHeaders,
)


class EditMediaAPI(APIPost, APIPut, APIDelete):
    """Deposit request class defining api endpoints for sword deposit.

       What's known as 'EM IRI' in the sword specification.

       HTTP verbs supported: PUT, POST, DELETE

    """

    parser_classes = (
        SWHFileUploadZipParser,
        SWHFileUploadTarParser,
    )

    def process_put(
        self, req, headers: ParsedRequestHeaders, collection_name: str, deposit_id: int
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
            raise DepositError(BAD_REQUEST, msg)

        return self._binary_upload(
            req, headers, collection_name, deposit_id=deposit_id, replace_archives=True
        )

    def process_post(
        self,
        req,
        headers: ParsedRequestHeaders,
        collection_name: str,
        deposit_id: Optional[int] = None,
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
            raise DepositError(BAD_REQUEST, msg)

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
