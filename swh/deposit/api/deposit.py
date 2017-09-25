# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from rest_framework import status

from .common import SWHBaseDeposit
from ..config import EDIT_SE_IRI
from ..errors import make_error_response
from ..errors import METHOD_NOT_ALLOWED
from ..parsers import SWHFileUploadParser, SWHAtomEntryParser
from ..parsers import SWHMultiPartParser


class SWHDeposit(SWHBaseDeposit):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'Col IRI' in the sword specification.

    HTTP verbs supported: POST

    """
    parser_classes = (SWHMultiPartParser,
                      SWHFileUploadParser,
                      SWHAtomEntryParser)

    def process_post(self, req, headers, client_name, deposit_id=None,
                     format=None):
        """Create a first deposit as:
        - archive deposit (1 zip)
        - multipart (1 zip + 1 atom entry)
        - atom entry

        Args:
            req (Request): the request holding the information to parse
                and inject in db
            client_name (str): the associated client

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
        if req.content_type == 'application/zip':
            data = self._binary_upload(req, headers, client_name)
        elif req.content_type.startswith('multipart/'):
            data = self._multipart_upload(req, headers, client_name)
        else:
            data = self._atom_entry(req, headers, client_name)

        return status.HTTP_201_CREATED, EDIT_SE_IRI, data

    def delete(self, req, client_name, deposit_id=None):
        """Routine to delete a resource.

        This is mostly not allowed except for the
        EM_IRI (cf. .api.deposit_update.SWHUpdateArchiveDeposit)

        """
        return make_error_response(req, METHOD_NOT_ALLOWED)

    def put(self, req, client_name, deposit_id=None, format=None):
        """This endpoint only supports POST.

        """
        return make_error_response(req, METHOD_NOT_ALLOWED)
