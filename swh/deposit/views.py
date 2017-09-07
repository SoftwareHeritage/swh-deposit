# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib
import logging

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView
from rest_framework import status
from rest_framework.views import APIView

from swh.core.config import SWHConfig
from swh.objstorage import get_objstorage
from swh.model.hashutil import hash_to_hex

from .models import Deposit, DepositRequest, DepositType
from .parsers import SWHFileUploadParser, SWHAtomEntryParser
from .parsers import SWHMultiPartParser, parse_xml


def index(req):
    return HttpResponse('SWH Deposit API - WIP')


class SWHView(SWHConfig, View):
    CONFIG_BASE_FILENAME = 'deposit/server'

    DEFAULT_CONFIG = {
        'max_upload_size': ('int', 209715200),
        'verbose': ('bool', False),
        'noop': ('bool', False),
    }

    def __init__(self, **config):
        super().__init__()
        self.config = self.parse_config_file()
        self.config.update(config)


class SWHServiceDocument(SWHView):
    def get(self, req, *args, **kwargs):
        context = {
            'max_upload_size': self.config['max_upload_size'],
            'verbose': self.config['verbose'],
            'noop': self.config['noop'],
        }
        return render(req, 'deposit/service_document.xml',
                      context, content_type='application/xml')


class SWHUser(ListView, SWHView):
    model = User

    def get(self, *args, **kwargs):
        if 'client_id' in kwargs:
            msg = 'Client '
            cs = self.get_queryset().filter(pk=kwargs['client_id'])
        else:
            msg = 'Clients'
            cs = self.get_queryset().all()
        return HttpResponse('%s: %s' % (msg, ','.join((str(c) for c in cs))))


class SWHDeposit(SWHView, APIView):
    """Deposit request class defining api endpoints for sword deposit.

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
        self.log = logging.getLogger('swh.deposit')

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

        return {
            'content-type': content_type,
            'content-length': content_length,
            'in-progress': in_progress,
            'content-disposition': content_disposition,
            'content-md5sum': content_md5sum,
            'packaging': packaging,
            'slug': slug,
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

    def _error(self, status, message):
        """Utility function to factorize error message dictionary.

        Args:
            status (status): Error status,
            message (str): Error message clarifying the status

        Returns:

            Dictionary with key 'error' detailing the 'status' and
            associated 'message'

        """
        return {
            'error': {
                'status': status,
                'content': message,
            },
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
                return self._error(
                    status.HTTP_403_FORBIDDEN,
                    'Upload size limit of %s exceeded. '
                    'Please consider sending the archive in '
                    'multiple steps.' % self.config['max_upload_size'])

            length = filehandler.size
            if length != content_length:
                return self._error(status.HTTP_412_PRECONDITION_FAILED,
                                   'Wrong length')

        if md5sum:
            _md5sum = self._compute_md5(filehandler)
            if _md5sum != md5sum:
                return self._error(status.HTTP_412_PRECONDITION_FAILED,
                                   'Wrong md5 hash')

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
        # binary_upload_headers_rule = {
        #     'MUST': ['Content-Disposition'],
        #     'SHOULD': ['Content-Type', 'Content-MD5', 'Packaging'],
        #     'MAY': ['In-Progress', 'On-Behalf-Of', 'Slug'],
        # }

        content_disposition = headers.get('content-disposition')
        if not content_disposition:
            return self._error(status.HTTP_400_BAD_REQUEST,
                               'CONTENT_DISPOSITION header is mandatory')

        filehandler = req.FILES['file']

        precondition_status_response = self._check_preconditions_on(
            filehandler,
            headers.get('content-md5sum'),
            headers.get('content-length'))

        if precondition_status_response:
            return precondition_status_response

        external_id = headers.get('slug')
        if not external_id:
            return self._error(
                status.HTTP_400_BAD_REQUEST,
                'You need to provide an unique external identifier')

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
        external_id = headers.get('slug')
        if not external_id:
            return self._error(
                status.HTTP_400_BAD_REQUEST,
                'You need to provide an unique external identifier')
        content_types_present = set()

        data = {
            'application/zip': None,  # expected archive
            'application/atom+xml': None,
        }
        for key, value in req.FILES.items():
            fh = value
            if fh.content_type in content_types_present:
                return self._error(
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    'Only 1 application/zip archive and 1 '
                    'atom+xml entry is supported.')

            content_types_present.add(fh.content_type)
            data[fh.content_type] = fh

        if len(content_types_present) != 2:
            return self._error(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                'You must provide both 1 application/zip '
                'and 1 atom+xml entry for multipart deposit.')

        filehandler = data['application/zip']
        precondition_status_response = self._check_preconditions_on(
            filehandler,
            headers.get('content-md5sum'))

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
            return self._error(
                status.HTTP_400_BAD_REQUEST,
                'Empty body request is not supported')

        external_id = req.data.get(
            '{http://www.w3.org/2005/Atom}external_identifier',
            headers.get('slug'))
        if not external_id:
            return self._error(
                status.HTTP_400_BAD_REQUEST,
                'You need to provide an unique external identifier')

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
            return HttpResponse(
                status=status.HTTP_400_BAD_REQUEST,
                content='Unknown client %s' % client_name)

        headers = self._read_headers(req)

        # binary upload according to sword 2.0 spec
        if req.content_type == 'application/zip':
            response_or_data = self._binary_upload(
                req, headers, client_name)
        elif req.content_type.startswith('multipart/'):
            response_or_data = self._multipart_upload(
                req, headers, client_name)
        else:
            response_or_data = self._atom_entry(
                req, headers, client_name)

        error = response_or_data.get('error')
        if error:
            return HttpResponse(**error)

        return render(req, 'deposit/deposit_receipt.xml',
                      context=response_or_data,
                      content_type='application/xml',
                      status=status.HTTP_201_CREATED)

    def put(self, req, client_name, format=None):
        """Update an archive (not allowed).

        Args:
            req (Request): the request holding the information to parse
                and inject in db
            client_name (str): the associated client

        Returns:
            HttpResponse 405 (not allowed)

        """
        return HttpResponse(
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            content='Archive are immutable, please post a new deposit'
            ' instead.')

    def delete(self, req, client_name, format=None):
        """Delete an archive (not allowed).

        Args:
            req (Request): the request holding the information to parse
                and inject in db
            client_name (str): the associated client

        Returns:
            HttpResponse 405 (not allowed)

        """
        return HttpResponse(
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            content='Archive are immutable, delete is not supported.')
