# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from rest_framework import status

from .common import SWHPostDepositAPI, ACCEPT_ARCHIVE_CONTENT_TYPES
from ..config import EDIT_SE_IRI
from ..errors import make_error_dict, BAD_REQUEST
from ..parsers import SWHFileUploadZipParser, SWHFileUploadTarParser
from ..parsers import SWHAtomEntryParser
from ..parsers import SWHMultiPartParser


class SWHDeposit(SWHPostDepositAPI):
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

    def additional_checks(self, req, headers, collection_name, deposit_id=None):
        slug = headers["slug"]
        if not slug:
            msg = "Missing SLUG header in request"
            verbose_description = "Provide in the SLUG header one identifier, for example the url pointing to the resource you are depositing."  # noqa
            return make_error_dict(BAD_REQUEST, msg, verbose_description)

        return {}

    def process_post(self, req, headers, collection_name, deposit_id=None):
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
            data = self._binary_upload(req, headers, collection_name)
        elif req.content_type.startswith("multipart/"):
            data = self._multipart_upload(req, headers, collection_name)
        else:
            data = self._atom_entry(req, headers, collection_name)

        return status.HTTP_201_CREATED, EDIT_SE_IRI, data
