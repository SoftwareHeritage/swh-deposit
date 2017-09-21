# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework import status

from ..models import DepositType
from ..parsers import SWHFileUploadParser, SWHAtomEntryParser
from ..parsers import SWHMultiPartParser
from ..errors import BAD_REQUEST, MEDIATION_NOT_ALLOWED, make_error
from ..errors import make_error_response

from .common import SWHBaseDeposit, ACCEPT_PACKAGINGS


class SWHDeposit(SWHBaseDeposit):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'Col IRI' in the sword specification.

    HTTP verbs supported: POST

    """
    parser_classes = (SWHMultiPartParser,
                      SWHFileUploadParser,
                      SWHAtomEntryParser)

    def post(self, req, client_name, format=None):
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
        try:
            self._type = DepositType.objects.get(name=client_name)
            self._user = User.objects.get(username=client_name)
        except (DepositType.DoesNotExist, User.DoesNotExist):
            error = make_error(BAD_REQUEST,
                               'Unknown client name %s' % client_name)
            return make_error_response(req, error['error'])

        headers = self._read_headers(req)

        if headers['on-behalf-of']:
            error = make_error(MEDIATION_NOT_ALLOWED,
                               'Mediation is not supported.')
            return make_error_response(req, error['error'])

        if req.content_type == 'application/zip':
            data = self._binary_upload(
                req, headers, client_name)
        elif req.content_type.startswith('multipart/'):
            data = self._multipart_upload(
                req, headers, client_name)
        else:
            data = self._atom_entry(
                req, headers, client_name)

        error = data.get('error')
        if error:
            return make_error_response(req, error)

        iris = self._make_iris(client_name, data['deposit_id'])

        data['packagings'] = ACCEPT_PACKAGINGS
        iris = self._make_iris(client_name, data['deposit_id'])
        data.update(iris)

        response = render(req, 'deposit/deposit_receipt.xml',
                          context=data,
                          content_type='application/xml',
                          status=status.HTTP_201_CREATED)
        response._headers['location'] = 'Location', data['edit_se_iri']

        return response
