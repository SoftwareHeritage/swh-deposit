# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status

from swh.objstorage import get_objstorage
from swh.model.hashutil import hash_to_hex

from ..config import SWHDefaultConfig
from ..models import Deposit, DepositRequest, DepositType
from ..parsers import SWHFileUploadParser, SWHAtomEntryParser
from ..parsers import SWHMultiPartParser, parse_xml
from ..errors import MAX_UPLOAD_SIZE_EXCEEDED, BAD_REQUEST, ERROR_CONTENT
from ..errors import CHECKSUM_MISMATCH, MEDIATION_NOT_ALLOWED, make_error
from ..errors import make_error_response

from .common import SWHAPIView, ACCEPT_PACKAGINGS


class SWHDeposit(SWHDefaultConfig, SWHAPIView):
    """Deposit request class defining api endpoints for sword deposit.

    What's known as 'Col IRI' in the sword specification.

    HTTP verbs supported: POST

    """
    parser_classes = (SWHMultiPartParser,
                      SWHFileUploadParser,
                      SWHAtomEntryParser)

    ADDITIONAL_CONFIG = {
        'objstorage': ('dict', {
            'cls': 'remote',
            'args': {
                'url': 'http://localhost:5002',
            }
        })
    }

    def __init__(self):
        super().__init__()
        self.objstorage = get_objstorage(**self.config['objstorage'])

    def _read_headers(self, req):
        """Read and unify the necessary headers from the request (those are
           not stored in the same location or not properly formatted).

        Args:
            req (Request): Input request

        Returns:
            Dictionary with the following keys (some associated values may be
              None):
                - content-type
                - content-length
                - in-progress
                - content-disposition
                - packaging
                - slug
                - on-behalf-of

        """
        meta = req._request.META
        # for k, v in meta.items():
        #     key = k.lower()
        #     if 'http_' in key:
        #         self.log.debug('%s: %s' % (k, v))
        content_type = req.content_type
        content_length = meta['CONTENT_LENGTH']
        if isinstance(content_length, str):
            content_length = int(content_length)

        # final deposit if not provided
        in_progress = meta.get('HTTP_IN_PROGRESS', False)
        content_disposition = meta.get('HTTP_CONTENT_DISPOSITION')
        if isinstance(in_progress, str):
            in_progress = in_progress.lower() == 'true'

        content_md5sum = meta.get('HTTP_CONTENT_MD5')
        if content_md5sum:
            content_md5sum = bytes.fromhex(content_md5sum)

        packaging = meta.get('HTTP_PACKAGING')
        slug = meta.get('HTTP_SLUG')
        on_behalf_of = meta.get('HTTP_ON_BEHALF_OF')

        return {
            'content-type': content_type,
            'content-length': content_length,
            'in-progress': in_progress,
            'content-disposition': content_disposition,
            'content-md5sum': content_md5sum,
            'packaging': packaging,
            'slug': slug,
            'on-behalf-of': on_behalf_of,
        }

    def _compute_md5(self, filehandler):
        """Compute uploaded file's md5 sum.

        Args:
            filehandler (InMemoryUploadedFile): the file to compute the md5
                hash

        Returns:
            the md5 checksum (str)

        """
        h = hashlib.md5()
        for chunk in filehandler:
            h.update(chunk)
        return h.digest()

    def _deposit_put(self, external_id, in_progress):
        """Save/Update a deposit in db.

        Args:
            external_id (str): The external identifier to associate to
              the deposit
            in_progress (dict): The deposit's status

        Returns:
            The Deposit instance saved or updated.

        """
        if in_progress is False:
            complete_date = timezone.now()
            status_type = 'ready'
        else:
            complete_date = None
            status_type = 'partial'

        try:
            deposit = Deposit.objects.get(external_id=external_id)
        except Deposit.DoesNotExist:
            deposit = Deposit(type=self._type,
                              external_id=external_id,
                              complete_date=complete_date,
                              status=status_type,
                              client=self._user)
        else:
            deposit.complete_date = complete_date
            deposit.status = status_type

        deposit.save()

        return deposit

    def _deposit_request_put(self, deposit, metadata):
        """Save a deposit request with metadata attached to a deposit.

        Args:
            deposit (Deposit): The deposit concerned by the request
            metadata (dict): The metadata to associate to the deposit

        Returns:
            The DepositRequest instance saved.

        """
        deposit_request = DepositRequest(
            deposit=deposit,
            metadata=metadata)

        deposit_request.save()

        return deposit_request

    def _archive_put(self, file):
        """Store archive file in objstorage and returns metadata about it.

        Args:
            file (InMemoryUploadedFile): archive's memory representation

        Returns:
            dict representing metadata about the archive

        """
        raw_content = b''.join(file.chunks())
        id = self.objstorage.add(content=raw_content)

        return {
            'archive': {
                'id': hash_to_hex(id),
                'name': file.name,
            }
        }

    def _check_preconditions_on(self, filehandler, md5sum,
                                content_length=None):
        """Check preconditions on provided file are respected. That is the
           length and/or the md5sum hash match the file's content.

        Args:
            filehandler (InMemoryUploadedFile): The file to check
            md5sum (hex str): md5 hash expected from the file's content
            content_length (int): the expected length if provided.

        Returns:
            Either none if no error or a dictionary with a key error
            detailing the problem.

        """
        if content_length:
            if content_length > self.config['max_upload_size']:
                return make_error(
                    MAX_UPLOAD_SIZE_EXCEEDED,
                    'Upload size limit exceeded (max %s bytes).' %
                    self.config['max_upload_size'],
                    'Please consider sending the archive in '
                    'multiple steps.')

            length = filehandler.size
            if length != content_length:
                return make_error(status.HTTP_412_PRECONDITION_FAILED,
                                  'Wrong length')

        if md5sum:
            _md5sum = self._compute_md5(filehandler)
            if _md5sum != md5sum:
                return make_error(
                    CHECKSUM_MISMATCH,
                    'Wrong md5 hash',
                    'The checksum sent %s and the actual checksum '
                    '%s does not match.' % (md5sum, _md5sum))

        return None

    def _binary_upload(self, req, headers, client_name):
        """Binary upload routine.

        Other than such a request, a 415 response is returned.

        Args:
            req (Request): the request holding information to parse
                and inject in db
            client_name (str): the associated client

        Returns:
            In the optimal case a dict with the following keys:
                - deposit_id (int): Deposit identifier
                - deposit_date (date): Deposit date
                - archive: None (no archive is provided here)

            Otherwise, a dictionary with the key error and the
            associated failures, either:

            - 400 (bad request) if the request is not providing an external
              identifier
            - 403 (forbidden) if the length of the archive exceeds the
              max size configured
            - 412 (precondition failed) if the length or md5 hash provided
              mismatch the reality of the archive
            - 415 (unsupported media type) if a wrong media type is provided

        """
        content_disposition = headers['content-disposition']
        if not content_disposition:
            return make_error(
                BAD_REQUEST,
                'CONTENT_DISPOSITION header is mandatory',
                'For a single archive deposit, the '
                'CONTENT_DISPOSITION header must be sent.')

        packaging = headers['packaging']
        if packaging and packaging not in ACCEPT_PACKAGINGS:
            return make_error(
                BAD_REQUEST,
                'Only packaging %s is supported' %
                ACCEPT_PACKAGINGS,
                'The packaging provided %s is not supported' % packaging)

        filehandler = req.FILES['file']

        precondition_status_response = self._check_preconditions_on(
            filehandler,
            headers['content-md5sum'],
            headers['content-length'])

        if precondition_status_response:
            return precondition_status_response

        external_id = headers['slug']
        if not external_id:
            return make_error(
                BAD_REQUEST,
                'You need to provide an unique external identifier',
                'The external identifier could be for example the identifier '
                'you use in your system.'
            )

        # actual storage of data
        metadata = self._archive_put(filehandler)
        deposit = self._deposit_put(external_id, headers['in-progress'])
        deposit_request = self._deposit_request_put(deposit, metadata)

        return {
            'deposit_id': deposit.id,
            'deposit_date': deposit_request.date,
            'archive': deposit_request.metadata['archive']['name'],
        }

    def _multipart_upload(self, req, headers, client_name):
        """Multipart upload supported with exactly:
        - 1 archive (zip)
        - 1 atom entry

        Other than such a request, a 415 response is returned.

        Args:
            req (Request): the request holding the information to parse
                and inject in db
            client_name (str): the associated client

        Returns:
            In the optimal case a dict with the following keys:
                - deposit_id (int): Deposit identifier
                - deposit_date (date): Deposit date
                - archive: None (no archive is provided here)

            Otherwise, a dictionary with the key error and the
            associated failures, either:

            - 400 (bad request) if the request is not providing an external
              identifier
            - 412 (precondition failed) if the potentially md5 hash provided
              mismatch the reality of the archive
            - 415 (unsupported media type) if a wrong media type is provided

        """
        external_id = headers['slug']
        if not external_id:
            return make_error(
                BAD_REQUEST,
                'You need to provide an unique external identifier',
                'The external identifier could be for example the identifier '
                'you use in your system.')

        content_types_present = set()

        data = {
            'application/zip': None,  # expected archive
            'application/atom+xml': None,
        }
        for key, value in req.FILES.items():
            fh = value
            if fh.content_type in content_types_present:
                return make_error(
                    ERROR_CONTENT,
                    'Only 1 application/zip archive and 1 '
                    'atom+xml entry is supported (as per sword2.0 '
                    'specification)',
                    'You provided more than 1 application/zip '
                    'or more than 1 application/atom+xml content-disposition '
                    'header in the multipart deposit')

            content_types_present.add(fh.content_type)
            data[fh.content_type] = fh

        if len(content_types_present) != 2:
            return make_error(
                ERROR_CONTENT,
                'You must provide both 1 application/zip '
                'and 1 atom+xml entry for multipart deposit',
                'You need to provide only 1 application/zip '
                'and 1 application/atom+xml content-disposition header '
                'in the multipart deposit')

        filehandler = data['application/zip']
        precondition_status_response = self._check_preconditions_on(
            filehandler,
            headers['content-md5sum'])

        if precondition_status_response:
            return precondition_status_response

        # actual storage of data
        metadata = self._archive_put(filehandler)
        atom_metadata = parse_xml(data['application/atom+xml'])
        metadata.update(atom_metadata)
        deposit = self._deposit_put(external_id, headers['in-progress'])
        deposit_request = self._deposit_request_put(deposit, metadata)

        return {
            'deposit_id': deposit.id,
            'deposit_date': deposit_request.date,
            'archive': deposit_request.metadata['archive']['name'],
        }

    def _atom_entry(self, req, headers, client_name):
        """Atom entry deposit.

        Args:
            req (Request): the request holding the information to parse
                and inject in db
            client_name (str): the associated client

        Returns:
            In the optimal case a dict with the following keys:
                - deposit_id: deposit id associated to the deposit
                - deposit_date: date of the deposit
                - archive: None (no archive is provided here)

            Otherwise, a dictionary with the key error and the
            associated failures, either:

            - 400 (bad request) if the request is not providing an external
              identifier
            - 400 (bad request) if the request's body is empty
            - 415 (unsupported media type) if a wrong media type is provided

        """
        if not req.data:
            return make_error(
                BAD_REQUEST,
                'Empty body request is not supported',
                'Atom entry deposit is supposed to send for metadata. '
                'If the body is empty, there is no metadata.')

        external_id = req.data.get(
            '{http://www.w3.org/2005/Atom}external_identifier',
            headers['slug'])
        if not external_id:
            return make_error(
                BAD_REQUEST,
                'You need to provide an unique external identifier',
                'The external identifier could be for example the identifier '
                'you use in your system.')

        deposit = self._deposit_put(external_id, headers['in-progress'])
        deposit_request = self._deposit_request_put(deposit, metadata=req.data)

        return {
            'deposit_id': deposit.id,
            'deposit_date': deposit_request.date,
            'archive': None,
        }

    def post(self, req, client_name, format=None):
        """Upload a file through possible request as:

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
        data['em_iri'] = iris['em_iri']
        data['edit_se_iri'] = iris['edit_se_iri']

        response = render(req, 'deposit/deposit_receipt.xml',
                          context=data,
                          content_type='application/xml',
                          status=status.HTTP_201_CREATED)
        response._headers['location'] = 'Location', data['edit_se_iri']

        return response

    def _make_iris(self, client_name, deposit_id):
        """Define the endpoints iri

        """
        return {
            'em_iri': reverse(
                'em_iri',
                args=[client_name, deposit_id]),
            'edit_se_iri': reverse(
                'edit_se_iri',
                args=[client_name, deposit_id])
        }
