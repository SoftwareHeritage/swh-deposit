# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict, Optional, Tuple

from rest_framework import status

from ..config import EDIT_SE_IRI
from ..parsers import (
    SWHAtomEntryParser,
    SWHFileUploadTarParser,
    SWHFileUploadZipParser,
    SWHMultiPartParser,
)
from .common import ACCEPT_ARCHIVE_CONTENT_TYPES, APIPost


class APIPostDeposit(APIPost):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'Col IRI' in the sword specification.

    HTTP verbs supported: POST

    """

    parser_classes = (
        SWHMultiPartParser,
        SWHFileUploadZipParser,
        SWHFileUploadTarParser,
        SWHAtomEntryParser,
    )

    def process_post(
        self,
        req,
        headers: Dict[str, Any],
        collection_name: str,
        deposit_id: Optional[int] = None,
    ) -> Tuple[int, str, Dict[str, Any]]:
        """Create a first deposit as:
        - archive deposit (1 zip)
        - multipart (1 zip + 1 atom entry)
        - atom entry

        Args:
            req (Request): the request holding the information to parse
                and inject in db
            collection_name (str): the associated client

        Returns:
            An http response (HttpResponse) according to the situation.

            If everything is ok, a 201 response (created) with a
            deposit receipt.

            Otherwise, depending on the upload, the following errors
            can be returned:

            - archive deposit:
                - 400 (bad request) if the request is not providing an external
                  identifier
                - 403 (forbidden) if the length of the archive exceeds the
                  max size configured
                - 412 (precondition failed) if the length or hash provided
                  mismatch the reality of the archive.
                - 415 (unsupported media type) if a wrong media type is
                  provided

            - multipart deposit:
                - 400 (bad request) if the request is not providing an external
                  identifier
                - 412 (precondition failed) if the potentially md5 hash
                  provided mismatch the reality of the archive
                - 415 (unsupported media type) if a wrong media type is
                  provided

            - Atom entry deposit:
                - 400 (bad request) if the request is not providing an external
                  identifier
                - 400 (bad request) if the request's body is empty
                - 415 (unsupported media type) if a wrong media type is
                  provided

        """
        assert deposit_id is None
        if req.content_type in ACCEPT_ARCHIVE_CONTENT_TYPES:
            data = self._binary_upload(
                req, headers, collection_name, check_slug_is_present=True
            )
        elif req.content_type.startswith("multipart/"):
            data = self._multipart_upload(
                req, headers, collection_name, check_slug_is_present=True
            )
        else:
            data = self._atom_entry(
                req, headers, collection_name, check_slug_is_present=True
            )

        return status.HTTP_201_CREATED, EDIT_SE_IRI, data
