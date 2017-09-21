# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status

from .common import SWHBaseDeposit, ACCEPT_PACKAGINGS
from ..parsers import SWHFileUploadParser, SWHAtomEntryParser
from ..parsers import SWHMultiPartParser

from ..models import DepositType
from ..errors import make_error, make_error_response, BAD_REQUEST
from ..errors import MEDIATION_NOT_ALLOWED


class SWHUpdateArchiveDeposit(SWHBaseDeposit):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'EM IRI' in the sword specification.

    HTTP verbs supported: PUT

    """
    parser_classes = (SWHFileUploadParser, )

    def put(self, req, client_name, deposit_id, format=None):
        """Replace existing content for the existing deposit.

        +header: Metadata-relevant (to extract metadata from the archive)

        source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_editingcontent_binary  # noqa

        Returns:
            204 No content

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

        if req.content_type != 'application/zip':
            error = make_error(BAD_REQUEST,
                               'Only application/zip is supported!')
            return make_error_response(req, error['error'])

        data = self._binary_upload(req, headers, client_name,
                                   deposit_id=deposit_id, update=True)

        error = data.get('error')
        if error:
            return make_error_response(req, error)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def post(self, req, client_name, deposit_id, format=None):
        """Add new content to the existing deposit.

        +header: Metadata-relevant (to extract metadata from the archive)

        source: http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_addingcontent_mediaresource  # noqa

        Returns:
            201 Created
            Headers: Location: [Cont-File-IRI]

            Body: [optional Deposit Receipt]

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
                req, headers, client_name, deposit_id)
        elif req.content_type.startswith('multipart/'):
            data = self._multipart_upload(
                req, headers, client_name, deposit_id)
        else:
            data = self._atom_entry(
                req, headers, client_name)

        error = data.get('error')
        if error:
            return make_error_response(req, error)

        data['packagings'] = ACCEPT_PACKAGINGS
        iris = self._make_iris(client_name, data['deposit_id'])
        data.update(iris)

        response = render(req, 'deposit/deposit_receipt.xml',
                          context=data,
                          content_type='application/xml',
                          status=status.HTTP_201_CREATED)
        response._headers['location'] = 'Location', iris['cont_file_iri']
        return response


class SWHUpdateMetadataDeposit(SWHBaseDeposit):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'Edit IRI' (and SE IRI) in the sword specification.

    HTTP verbs supported: POST (SE IRI), PUT (Edit IRI)

    """
    parser_classes = (SWHMultiPartParser, SWHAtomEntryParser)

    def put(self, req, client_name, deposit_id, format=None):
        """Replace existing deposit's metadata/archive with new ones.

        source:
        - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_editingcontent_metadata  # noqa
        - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_editingcontent_multipart  # noqa

        Returns:
            204 No content

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

        if req.content_type.startswith('multipart/'):
            data = self._multipart_upload(
                req, headers, client_name, deposit_id=deposit_id, update=True)
        else:
            data = self._atom_entry(
                req, headers, client_name, deposit_id=deposit_id, update=True)

        error = data.get('error')
        if error:
            return make_error_response(req, error)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def post(self, req, client_name, deposit_id, format=None):
        """Add new metadata/archive to existing deposit.

        source:
        - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_addingcontent_metadata  # noqa
        - http://swordapp.github.io/SWORDv2-Profile/SWORDProfile.html#protocoloperations_addingcontent_multipart  # noqa

        Returns:
            201 Created
            Location: [EM-IRI]

            [optional Deposit Receipt]

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

        if req.content_type.startswith('multipart/'):
            data = self._multipart_upload(
                req, headers, client_name, deposit_id=deposit_id)
        else:
            data = self._atom_entry(
                req, headers, client_name, deposit_id=deposit_id)

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
        response._headers['location'] = 'Location', data['em_iri']

        return response
