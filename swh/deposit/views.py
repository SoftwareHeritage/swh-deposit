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
from rest_framework_xml.parsers import XMLParser

from swh.core.config import SWHConfig
from swh.objstorage import get_objstorage
from swh.model.hashutil import hash_to_hex

from .models import Deposit, DepositRequest, DepositType
from .parsers import SWHFileUploadParser, SWHAtomEntryParser
from .parsers import SWHMultiPartParser


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
    """This class defines the create behavior of our rest api."""
    parser_classes = (SWHMultiPartParser, SWHFileUploadParser,
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
        """Read the necessary headers from the request.

        # Content-Type, Content-Disposition, Packaging required header
        # if no Content-Type header, assume 'application/octet-stream'
        # source: https://www.w3.org/Protocols/rfc2616/rfc2616-sec7.html#sec7.2.1  # noqa
        """
        # for k, v in req._request.META.items():
        #     key = k.lower()
        #     if 'http_' in key:
        #         self.log.debug('%s: %s' % (k, v))
        meta = req._request.META
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

        Returns:
            md5 checksum

        """
        h = hashlib.md5()
        for chunk in filehandler:
            h.update(chunk)
        return h.digest()

    def _compute_length(self, filehandler):
        """Compute uploaded file's length.

        """
        content_length = 0
        for chunk in filehandler:
            content_length += len(chunk)
        return content_length

    def _deposit_put(self, external_id, in_progress):
        """Save/Update a deposit in db.

        Args:
            external_id (str): The external identifier to associate to
              the deposit
            in_progress (dict): The deposit's status

        Returns:
            The Deposit instance.

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
            The DepositRequest instance.

        """
        deposit_request = DepositRequest(
            deposit=deposit,
            metadata=metadata)

        deposit_request.save()

        return deposit_request

    def _archive_put(self, file):
        """Store archive file in objstorage.

        Args:
            file (InMemoryUploadedFile): archive's memory representation

        Returns:
            dict representing metadata to store about the archive.

        """
        raw_content = b''.join(file.chunks())
        id = self.objstorage.add(content=raw_content)

        return {
            'archive': {
                'id': hash_to_hex(id),
                'name': file.name,
            }
        }

    def _binary_upload(self, req, client_name):
        """Binary upload routine.

        """
        headers = self._read_headers(req)

        # binary_upload_headers_rule = {
        #     'MUST': ['Content-Disposition'],
        #     'SHOULD': ['Content-Type', 'Content-MD5', 'Packaging'],
        #     'MAY': ['In-Progress', 'On-Behalf-Of', 'Slug'],
        # }

        filehandler = req.FILES['file']

        if 'content-length' in headers:
            if headers['content-length'] > self.config['max_upload_size']:
                return HttpResponse(
                    status=status.HTTP_403_FORBIDDEN,
                    content='Upload size limit of %s exceeded. '
                    'Please consider sending the archive in '
                    'multiple steps.' % self.config['max_upload_size'])

            length = self._compute_length(filehandler)
            if length != headers['content-length']:
                return HttpResponse(status=status.HTTP_412_PRECONDITION_FAILED,
                                    content='Wrong length')

        if 'content-md5sum' in headers:
            md5sum = self._compute_md5(filehandler)
            if md5sum != headers['content-md5sum']:
                return HttpResponse(status=status.HTTP_412_PRECONDITION_FAILED,
                                    content='Wrong md5 hash')

        external_id = headers.get('slug')
        if not external_id:
            return HttpResponse(
                status=status.HTTP_400_BAD_REQUEST,
                content='You need to provide an unique external identifier')

        # actual storage of data
        metadata = self._archive_put(filehandler)
        deposit = self._deposit_put(external_id, headers['in-progress'])
        deposit_request = self._deposit_request_put(deposit, metadata)

        return deposit_request

    def _multipart_upload(self, req, client_name):
        """Multipart supported with at most:
        - 1 archive
        - 1 atom entry

        Other than such, a 415 response is returned.

        """
        headers = self._read_headers(req)

        external_id = headers.get('slug')
        if not external_id:
            return HttpResponse(
                status=status.HTTP_400_BAD_REQUEST,
                content='You need to provide an unique external identifier')
        content_types_present = set()

        data = {
            'application/zip': None,  # expected archive
            'application/atom+xml': None,
        }
        for key, value in req.FILES.items():
            fh = value
            if fh.content_type in content_types_present:
                return HttpResponse(
                    status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content='Only 1 application/zip archive and 1 '
                    'atom+xml entry is supported.')

            content_types_present.add(fh.content_type)
            data[fh.content_type] = fh

        if len(content_types_present) != 2:
            return HttpResponse(
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content='You must provide both 1 application/zip '
                'and 1 atom+xml entry for multipart deposit.')

        # actual storage of data
        metadata = self._archive_put(data['application/zip'])
        atom_metadata = XMLParser().parse(data['application/atom+xml'])
        metadata.update(atom_metadata)
        deposit = self._deposit_put(external_id, headers['in-progress'])
        deposit_request = self._deposit_request_put(deposit, metadata)

        return deposit_request

    def _atom_entry(self, req, client_name, format=None):
        """Atom entry deposit.

        """
        headers = self._read_headers(req)

        if not req.data:
            return HttpResponse(
                status=status.HTTP_400_BAD_REQUEST,
                content='Empty body request is not supported')

        external_id = req.data.get(
            '{http://www.w3.org/2005/Atom}external_identifier',
            headers.get('slug'))
        if not external_id:
            return HttpResponse(
                status=status.HTTP_400_BAD_REQUEST,
                content='You need to provide an unique external identifier')

        deposit = self._deposit_put(external_id, headers['in-progress'])
        deposit_request = self._deposit_request_put(deposit, metadata=req.data)

        return deposit_request

    def post(self, req, client_name, format=None):
        """Upload a file.

        """
        try:
            self._type = DepositType.objects.get(name=client_name)
            self._user = User.objects.get(username=client_name)
        except (DepositType.DoesNotExist, User.DoesNotExist):
            return HttpResponse(
                status=status.HTTP_400_BAD_REQUEST,
                content='Unknown client %s' % client_name)

        content_disposition = req._request.META.get('HTTP_CONTENT_DISPOSITION')
        if content_disposition:  # binary upload according to sword 2.0 spec
            r = self._binary_upload(req, client_name)
        elif req.content_type.startswith('multipart/'):
            r = self._multipart_upload(req, client_name)
        else:
            r = self._atom_entry(req, client_name)

        if isinstance(r, HttpResponse):
            return r

        deposit_request = r
        context = {
            'deposit_id': deposit_request.deposit.id,
            'deposit_date': deposit_request.date,
            'archive': deposit_request.metadata,
        }
        return render(req, 'deposit/deposit_receipt.xml',
                      context,
                      content_type='application/xml',
                      status=status.HTTP_201_CREATED)

    def put(self, req, client_name, format=None):
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)
