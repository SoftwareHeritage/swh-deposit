# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from abc import ABCMeta, abstractmethod


from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from swh.objstorage import get_objstorage
from swh.model.hashutil import hash_to_hex

from ..config import SWHDefaultConfig
from ..models import Deposit, DepositRequest, DepositType, DepositRequestType
from ..parsers import parse_xml
from ..errors import MAX_UPLOAD_SIZE_EXCEEDED, BAD_REQUEST, ERROR_CONTENT
from ..errors import CHECKSUM_MISMATCH, make_error, MEDIATION_NOT_ALLOWED
from ..errors import make_error_response, NOT_FOUND


ACCEPT_PACKAGINGS = ['http://purl.org/net/sword/package/SimpleZip']
ACCEPT_CONTENT_TYPES = ['application/zip']


def index(req):
    return HttpResponse('SWH Deposit API')


class SWHAPIView(APIView):
    """Mixin intended as a based API view to enforce the basic
       authentication check

    """
    pass


class SWHBaseDeposit(SWHDefaultConfig, SWHAPIView, metaclass=ABCMeta):
    """Base deposit request class sharing multiple common behaviors.

    """
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
        deposit_request_types = DepositRequestType.objects.all()
        self.deposit_request_types = {
            type.name: type for type in deposit_request_types
        }

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
        metadata_relevant = meta.get('HTTP_METADATA_RELEVANT')

        return {
            'content-type': content_type,
            'content-length': content_length,
            'in-progress': in_progress,
            'content-disposition': content_disposition,
            'content-md5sum': content_md5sum,
            'packaging': packaging,
            'slug': slug,
            'on-behalf-of': on_behalf_of,
            'metadata-relevant': metadata_relevant,
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

    def _deposit_put(self, deposit_id=None, in_progress=False,
                     external_id=None):
        """Save/Update a deposit in db.

        Args:
            deposit_id (int): deposit identifier
            in_progress (dict): The deposit's status
            external_id (str): The external identifier to associate to
              the deposit

        Returns:
            The Deposit instance saved or updated.

        """
        if in_progress is False:
            complete_date = timezone.now()
            status_type = 'ready'
        else:
            complete_date = None
            status_type = 'partial'

        if not deposit_id:
            deposit = Deposit(type=self._type,
                              external_id=external_id,
                              complete_date=complete_date,
                              status=status_type,
                              client=self._user)
        else:
            deposit = Deposit.objects.get(pk=deposit_id)

            # update metadata
            deposit.complete_date = complete_date
            deposit.status = status_type

        deposit.save()

        return deposit

    def _deposit_request_put(self, deposit, deposit_request_data,
                             replace_metadata=False, replace_archives=False):
        """Save a deposit request with metadata attached to a deposit.

        Args:
            deposit (Deposit): The deposit concerned by the request
            deposit_request_data (dict): The dictionary with at most 2 deposit
            request types (archive, metadata) to associate to the deposit
            replace_metadata (bool): Flag defining if we add or update
              existing metadata to the deposit
            replace_archives (bool): Flag defining if we add or update
              archives to existing deposit

        Returns:
            The DepositRequest instance saved.

        """
        if replace_metadata:
            DepositRequest.objects.filter(
                deposit=deposit,
                type=self.deposit_request_types['metadata']).delete()
        if replace_archives:
            DepositRequest.objects.filter(
                deposit=deposit,
                type=self.deposit_request_types['archives']).delete()

        for type, metadata in deposit_request_data.items():
            deposit_request = DepositRequest(
                type=self.deposit_request_types[type],
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

    def _binary_upload(self, req, headers, client_name,
                       deposit_id=None, update=False):
        """Binary upload routine.

        Other than such a request, a 415 response is returned.

        Args:
            req (Request): the request holding information to parse
                and inject in db
            headers (dict): request headers formatted
            client_name (str): the associated client
            deposit_id (id): deposit identifier if provided
            replace_metadata (bool): 'Update or add' request to existing
              deposit. Default to False, this adds new metadata request to
              existing ones
            replace_archives (bool): 'Update or add' request to existing
              deposit. Default to False, this adds new archives to existing
              ones.

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

        # actual storage of data
        archive_metadata = self._archive_put(filehandler)
        deposit = self._deposit_put(deposit_id=deposit_id,
                                    in_progress=headers['in-progress'],
                                    external_id=external_id)
        deposit_request = self._deposit_request_put(
            deposit, {'archive': archive_metadata})

        return {
            'deposit_id': deposit.id,
            'deposit_date': deposit_request.date,
            'archive': deposit_request.metadata['archive']['name'],
        }

    def _multipart_upload(self, req, headers, client_name,
                          deposit_id=None, replace_metadata=False,
                          replace_archives=False):
        """Multipart upload supported with exactly:
        - 1 archive (zip)
        - 1 atom entry

        Other than such a request, a 415 response is returned.

        Args:
            req (Request): the request holding information to parse
                and inject in db
            headers (dict): request headers formatted
            client_name (str): the associated client
            deposit_id (id): deposit identifier if provided
            replace_metadata (bool): 'Update or add' request to existing
              deposit. Default to False, this adds new metadata request to
              existing ones
            replace_archives (bool): 'Update or add' request to existing
              deposit. Default to False, this adds new archives to existing
              ones.

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
        archive_metadata = self._archive_put(filehandler)
        atom_metadata = parse_xml(data['application/atom+xml'])
        deposit = self._deposit_put(deposit_id=deposit_id,
                                    in_progress=headers['in-progress'],
                                    external_id=external_id)
        deposit_request_data = {
            'archive': archive_metadata,
            'metadata': atom_metadata,
        }
        deposit_request = self._deposit_request_put(
            deposit, deposit_request_data, replace_metadata, replace_archives)

        return {
            'deposit_id': deposit.id,
            'deposit_date': deposit_request.date,
            'archive': archive_metadata['archive']['name'],
        }

    def _atom_entry(self, req, headers, client_name,
                    deposit_id=None,
                    replace_metadata=False,
                    replace_archives=False):
        """Atom entry deposit.

        Args:
            req (Request): the request holding information to parse
                and inject in db
            headers (dict): request headers formatted
            client_name (str): the associated client
            deposit_id (id): deposit identifier if provided
            replace_metadata (bool): 'Update or add' request to existing
              deposit. Default to False, this adds new metadata request to
              existing ones
            replace_archives (bool): 'Update or add' request to existing
              deposit. Default to False, this adds new archives to existing
              ones.

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

        deposit = self._deposit_put(deposit_id=deposit_id,
                                    in_progress=headers['in-progress'],
                                    external_id=external_id)
        deposit_request = self._deposit_request_put(
            deposit, {'metadata': req.data},
            replace_metadata, replace_archives)

        return {
            'deposit_id': deposit.id,
            'deposit_date': deposit_request.date,
            'archive': None,
        }

    def _make_iris(self, client_name, deposit_id):
        """Define the IRI endpoints

        """
        return {
            'em_iri': reverse(
                'em_iri',
                args=[client_name, deposit_id]),
            'edit_se_iri': reverse(
                'edit_se_iri',
                args=[client_name, deposit_id]),
            'cont_file_iri': reverse(
                'cont_file_iri',
                args=[client_name, deposit_id]),
        }

    def post(self, req, client_name, deposit_id=None, format=None):
        try:
            self._type = DepositType.objects.get(name=client_name)
            self._user = User.objects.get(username=client_name)
        except (DepositType.DoesNotExist, User.DoesNotExist):
            error = make_error(BAD_REQUEST,
                               'Unknown client name %s' % client_name)
            return make_error_response(req, error['error'])

        if deposit_id:
            try:
                deposit = Deposit.objects.get(pk=deposit_id)
            except Deposit.DoesNotExist:
                error = make_error(NOT_FOUND,
                                   'Deposit with id %s does not exist' %
                                   deposit_id)
                return make_error_response(req, error['error'])

            if deposit.status != 'partial':
                error = make_error(
                    BAD_REQUEST,
                    'You cannot update a deposit in status ready.')
                return make_error_response(req, error['error'])

        headers = self._read_headers(req)

        if headers['on-behalf-of']:
            error = make_error(MEDIATION_NOT_ALLOWED,
                               'Mediation is not supported.')
            return make_error_response(req, error['error'])

        data = self.process_post(req, headers, client_name, deposit_id)

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
        response = self.update_post_response(response, data)
        return response

    @abstractmethod
    def update_post_response(self, response, data):
        """Routine to permit the post response override (e.g add some headers
           in the response.)

        """
        pass

    @abstractmethod
    def process_post(self, req, client_name, deposit_id=None, format=None):
        """Routine to permit the post processing to occur.

        """
        pass

    def put(self, req, client_name, deposit_id, format=None):
        try:
            self._type = DepositType.objects.get(name=client_name)
            self._user = User.objects.get(username=client_name)
        except (DepositType.DoesNotExist, User.DoesNotExist):
            error = make_error(BAD_REQUEST,
                               'Unknown client name %s' % client_name)
            return make_error_response(req, error['error'])

        if deposit_id:
            try:
                deposit = Deposit.objects.get(pk=deposit_id)
            except Deposit.DoesNotExist:
                error = make_error(NOT_FOUND,
                                   'Deposit with id %s does not exist' %
                                   deposit_id)
                return make_error_response(req, error['error'])

            if deposit.status != 'partial':
                error = make_error(
                    BAD_REQUEST,
                    'You cannot update a deposit in status ready.')
                return make_error_response(req, error['error'])

        headers = self._read_headers(req)

        if headers['on-behalf-of']:
            error = make_error(MEDIATION_NOT_ALLOWED,
                               'Mediation is not supported.')
            return make_error_response(req, error['error'])

        data = self.process_put(req, headers, client_name, deposit_id)

        error = data.get('error')
        if error:
            return make_error_response(req, error)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    def process_put(self, req, client_name, deposit_id=None, update=False,
                    format=None):
        """Routine to permit the put processing to occur.

        """
        pass
