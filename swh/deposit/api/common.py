# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from abc import ABCMeta, abstractmethod


from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from django.contrib.auth.middleware import AuthenticationMiddleware

from ..config import SWHDefaultConfig, EDIT_SE_IRI, EM_IRI, CONT_FILE_IRI
from ..config import ARCHIVE_KEY, METADATA_KEY
from ..models import Deposit, DepositRequest, DepositCollection
from ..models import DepositRequestType, DepositClient
from ..parsers import parse_xml
from ..errors import MAX_UPLOAD_SIZE_EXCEEDED, BAD_REQUEST, ERROR_CONTENT
from ..errors import CHECKSUM_MISMATCH, make_error_dict, MEDIATION_NOT_ALLOWED
from ..errors import make_error_response_from_dict, FORBIDDEN
from ..errors import NOT_FOUND, make_error_response, METHOD_NOT_ALLOWED


ACCEPT_PACKAGINGS = ['http://purl.org/net/sword/package/SimpleZip']
ACCEPT_CONTENT_TYPES = ['application/zip']


class SWHAPIView(APIView):
    """Mixin intended as a based API view to enforce the basic
       authentication check

    """
    authentication_classes = (BasicAuthentication, SessionAuthentication, )


class SWHPrivateAPIView(SWHAPIView):
    """Mixin intended as private api (so no authentication) based API view
       (for the private ones).

    """
    authentication_classes = ()


class SWHBaseDeposit(SWHDefaultConfig, SWHAPIView, metaclass=ABCMeta):
    """Base deposit request class sharing multiple common behaviors.

    """
    def __init__(self):
        super().__init__()
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
        content_type = req.content_type
        content_length = meta.get('CONTENT_LENGTH')
        if content_length and isinstance(content_length, str):
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
            deposit = Deposit(collection=self._collection,
                              external_id=external_id,
                              complete_date=complete_date,
                              status=status_type,
                              client=self._client)
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
            None

        """
        if replace_metadata:
            DepositRequest.objects.filter(
                deposit=deposit,
                type=self.deposit_request_types[METADATA_KEY]).delete()

        if replace_archives:
            DepositRequest.objects.filter(
                deposit=deposit,
                type=self.deposit_request_types[ARCHIVE_KEY]).delete()

        deposit_request = None

        archive_file = deposit_request_data.get(ARCHIVE_KEY)
        if archive_file:
            deposit_request = DepositRequest(
                type=self.deposit_request_types[ARCHIVE_KEY],
                deposit=deposit,
                archive=archive_file)
            deposit_request.save()

        metadata = deposit_request_data.get(METADATA_KEY)
        if metadata:
            deposit_request = DepositRequest(
                type=self.deposit_request_types[METADATA_KEY],
                deposit=deposit,
                metadata=metadata)
            deposit_request.save()

        assert deposit_request is not None

    def _delete_archives(self, collection_name, deposit_id):
        """Delete archives reference from the deposit id.

        """
        try:
            deposit = Deposit.objects.get(pk=deposit_id)
        except Deposit.DoesNotExist:
            return make_error_dict(
                NOT_FOUND,
                'The deposit %s does not exist' % deposit_id)
        DepositRequest.objects.filter(
            deposit=deposit,
            type=self.deposit_request_types[ARCHIVE_KEY]).delete()

        return {}

    def _delete_deposit(self, collection_name, deposit_id):
        """Delete deposit reference.

        Args:
            collection_name (str): Client's name
            deposit_id (id): The deposit to delete

        Returns
            Empty dict when ok.
            Dict with error key to describe the failure.

        """
        try:
            deposit = Deposit.objects.get(pk=deposit_id)
        except Deposit.DoesNotExist:
            return make_error_dict(
                NOT_FOUND,
                'The deposit %s does not exist' % deposit_id)

        if deposit.collection.name != collection_name:
            summary = 'Cannot delete a deposit from another collection'
            description = "Deposit %s does not belong to the collection %s" % (
                deposit_id, collection_name)
            return make_error_dict(
                BAD_REQUEST,
                summary=summary,
                verbose_description=description)

        DepositRequest.objects.filter(deposit=deposit).delete()
        deposit.delete()

        return {}

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
                return make_error_dict(
                    MAX_UPLOAD_SIZE_EXCEEDED,
                    'Upload size limit exceeded (max %s bytes).' %
                    self.config['max_upload_size'],
                    'Please consider sending the archive in '
                    'multiple steps.')

            length = filehandler.size
            if length != content_length:
                return make_error_dict(status.HTTP_412_PRECONDITION_FAILED,
                                       'Wrong length')

        if md5sum:
            _md5sum = self._compute_md5(filehandler)
            if _md5sum != md5sum:
                return make_error_dict(
                    CHECKSUM_MISMATCH,
                    'Wrong md5 hash',
                    'The checksum sent %s and the actual checksum '
                    '%s does not match.' % (md5sum, _md5sum))

        return None

    def _binary_upload(self, req, headers, collection_name, deposit_id=None,
                       replace_metadata=False, replace_archives=False):
        """Binary upload routine.

        Other than such a request, a 415 response is returned.

        Args:
            req (Request): the request holding information to parse
                and inject in db
            headers (dict): request headers formatted
            collection_name (str): the associated client
            deposit_id (id): deposit identifier if provided
            replace_metadata (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
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
        content_length = headers['content-length']
        if not content_length:
            return make_error_dict(
                BAD_REQUEST,
                'CONTENT_LENGTH header is mandatory',
                'For archive deposit, the '
                'CONTENT_LENGTH header must be sent.')

        content_disposition = headers['content-disposition']
        if not content_disposition:
            return make_error_dict(
                BAD_REQUEST,
                'CONTENT_DISPOSITION header is mandatory',
                'For archive deposit, the '
                'CONTENT_DISPOSITION header must be sent.')

        packaging = headers['packaging']
        if packaging and packaging not in ACCEPT_PACKAGINGS:
            return make_error_dict(
                BAD_REQUEST,
                'Only packaging %s is supported' %
                ACCEPT_PACKAGINGS,
                'The packaging provided %s is not supported' % packaging)

        filehandler = req.FILES['file']

        precondition_status_response = self._check_preconditions_on(
            filehandler, headers['content-md5sum'], content_length)

        if precondition_status_response:
            return precondition_status_response

        external_id = headers['slug']

        # actual storage of data
        archive_metadata = filehandler
        deposit = self._deposit_put(deposit_id=deposit_id,
                                    in_progress=headers['in-progress'],
                                    external_id=external_id)
        self._deposit_request_put(
            deposit, {ARCHIVE_KEY: archive_metadata},
            replace_metadata=replace_metadata,
            replace_archives=replace_archives)

        return {
            'deposit_id': deposit.id,
            'deposit_date': deposit.reception_date,
            'archive': filehandler.name,
        }

    def _multipart_upload(self, req, headers, collection_name,
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
            collection_name (str): the associated client
            deposit_id (id): deposit identifier if provided
            replace_metadata (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
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
                return make_error_dict(
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
            return make_error_dict(
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
        atom_metadata = parse_xml(data['application/atom+xml'])
        deposit = self._deposit_put(deposit_id=deposit_id,
                                    in_progress=headers['in-progress'],
                                    external_id=external_id)
        deposit_request_data = {
            ARCHIVE_KEY: filehandler,
            METADATA_KEY: atom_metadata,
        }
        self._deposit_request_put(
            deposit, deposit_request_data, replace_metadata, replace_archives)

        return {
            'deposit_id': deposit.id,
            'deposit_date': deposit.reception_date,
            'archive': filehandler.name,
        }

    def _atom_entry(self, req, headers, collection_name,
                    deposit_id=None,
                    replace_metadata=False,
                    replace_archives=False):
        """Atom entry deposit.

        Args:
            req (Request): the request holding information to parse
                and inject in db
            headers (dict): request headers formatted
            collection_name (str): the associated client
            deposit_id (id): deposit identifier if provided
            replace_metadata (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new metadata request to
              existing ones. Otherwise, this will replace existing metadata.
            replace_archives (bool): 'Update or add' request to existing
              deposit. If False (default), this adds new archive request to
              existing ones. Otherwise, this will replace existing archives.
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
            return make_error_dict(
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
        self._deposit_request_put(
            deposit, {METADATA_KEY: req.data},
            replace_metadata, replace_archives)

        return {
            'deposit_id': deposit.id,
            'deposit_date': deposit.reception_date,
            'archive': None,
        }

    def _empty_post(self, req, headers, collection_name, deposit_id):
        """Empty post to finalize an empty deposit.

        Args:
            req (Request): the request holding information to parse
                and inject in db
            headers (dict): request headers formatted
            collection_name (str): the associated client
            deposit_id (id): deposit identifier

        Returns:
            Dictionary of result with the deposit's id, the date
            it was completed and no archive.

        """
        deposit = Deposit.objects.get(pk=deposit_id)
        deposit.complete_date = timezone.now()
        deposit.status = 'ready'
        deposit.save()

        return {
            'deposit_id': deposit_id,
            'deposit_date': deposit.complete_date,
            'archive': None,
        }

    def _make_iris(self, collection_name, deposit_id):
        """Define the IRI endpoints

        Args:
            collection_name (str): client/collection's name
            deposit_id (id): Deposit identifier

        Returns:
            Dictionary of keys with the iris' urls.

        """
        return {
            EM_IRI: reverse(
                EM_IRI,
                args=[collection_name, deposit_id]),
            EDIT_SE_IRI: reverse(
                EDIT_SE_IRI,
                args=[collection_name, deposit_id]),
            CONT_FILE_IRI: reverse(
                CONT_FILE_IRI,
                args=[collection_name, deposit_id]),
        }

    def additional_checks(self, req, collection_name, deposit_id=None):
        """Permit the child class to enrich with additional checks.

        Returns:
            dict with 'error' detailing the problem.

        """
        return {}

    def checks(self, req, collection_name, deposit_id=None):
        try:
            self._collection = DepositCollection.objects.get(
                name=collection_name)
        except DepositCollection.DoesNotExist:
            return make_error_dict(
                NOT_FOUND,
                'Unknown collection name %s' % collection_name)

        try:
            username = req.user.username
            self._client = DepositClient.objects.get(username=username)
        except DepositClient.DoesNotExist:
            return make_error_dict(NOT_FOUND,
                                   'Unknown client name %s' % username)

        if self._collection.id not in self._client.collections:
            return make_error_dict(FORBIDDEN,
                                   'Client %s cannot access collection %s' % (
                                       username, collection_name))

        if deposit_id:
            try:
                deposit = Deposit.objects.get(pk=deposit_id)
            except Deposit.DoesNotExist:
                return make_error_dict(
                    NOT_FOUND,
                    'Deposit with id %s does not exist' %
                    deposit_id)

            checks = self.restrict_access(req, deposit)
            if checks:
                return checks

        headers = self._read_headers(req)
        if headers['on-behalf-of']:
            return make_error_dict(MEDIATION_NOT_ALLOWED,
                                   'Mediation is not supported.')

        checks = self.additional_checks(req, collection_name, deposit_id)
        if 'error' in checks:
            return checks

        return {'headers': headers}

    def restrict_access(self, req, deposit=None):
        if deposit:
            if req.method != 'GET' and deposit.status != 'partial':
                summary = "You can only act on deposit with status 'partial'"
                description = "This deposit has status '%s'" % deposit.status
                return make_error_dict(
                    BAD_REQUEST, summary=summary,
                    verbose_description=description)

    def get(self, req, *args, **kwargs):
        return make_error_response(req, METHOD_NOT_ALLOWED)

    def post(self, req, *args, **kwargs):
        return make_error_response(req, METHOD_NOT_ALLOWED)

    def put(self, req, *args, **kwargs):
        return make_error_response(req, METHOD_NOT_ALLOWED)

    def delete(self, req, *args, **kwargs):
        return make_error_response(req, METHOD_NOT_ALLOWED)


class SWHGetDepositAPI(SWHBaseDeposit, metaclass=ABCMeta):
    """Mixin for class to support GET method.

    """
    def get(self, req, collection_name, deposit_id, format=None):
        """Endpoint to create/add resources to deposit.

        Returns:
            200 response when no error during routine occurred
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        checks = self.checks(req, collection_name, deposit_id)
        if 'error' in checks:
            return make_error_response_from_dict(req, checks['error'])

        status, content, content_type = self.process_get(
            req, collection_name, deposit_id)

        return HttpResponse(content, status=status, content_type=content_type)

    @abstractmethod
    def process_get(self, req, collection_name, deposit_id):
        """Routine to deal with the deposit's get processing.

        Returns:
            Tuple status, stream of content, content-type

        """
        pass


class SWHPostDepositAPI(SWHBaseDeposit, metaclass=ABCMeta):
    """Mixin for class to support DELETE method.

    """
    def post(self, req, collection_name, deposit_id=None, format=None):
        """Endpoint to create/add resources to deposit.

        Returns:
            204 response when no error during routine occurred.
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist


        """
        checks = self.checks(req, collection_name, deposit_id)
        if 'error' in checks:
            return make_error_response_from_dict(req, checks['error'])

        headers = checks['headers']
        _status, _iri_key, data = self.process_post(
            req, headers, collection_name, deposit_id)

        error = data.get('error')
        if error:
            return make_error_response_from_dict(req, error)

        data['packagings'] = ACCEPT_PACKAGINGS
        iris = self._make_iris(collection_name, data['deposit_id'])
        data.update(iris)
        response = render(req, 'deposit/deposit_receipt.xml',
                          context=data,
                          content_type='application/xml',
                          status=_status)
        response._headers['location'] = 'Location', data[_iri_key]
        return response

    @abstractmethod
    def process_post(self, req, headers, collection_name, deposit_id=None):
        """Routine to deal with the deposit's processing.

        Returns
            Tuple of:
            - response status code (200, 201, etc...)
            - key iri (EM_IRI, EDIT_SE_IRI, etc...)
            - dictionary of the processing result

        """
        pass


class SWHPutDepositAPI(SWHBaseDeposit, metaclass=ABCMeta):
    """Mixin for class to support PUT method.

    """
    def put(self, req, collection_name, deposit_id, format=None):
        """Endpoint to update deposit resources.

        Returns:
            204 response when no error during routine occurred.
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist
        """
        checks = self.checks(req, collection_name, deposit_id)
        if 'error' in checks:
            return make_error_response_from_dict(req, checks['error'])

        headers = checks['headers']
        data = self.process_put(req, headers, collection_name, deposit_id)

        error = data.get('error')
        if error:
            return make_error_response_from_dict(req, error)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @abstractmethod
    def process_put(self, req, headers, collection_name, deposit_id):
        """Routine to deal with updating a deposit in some way.

        Returns
            dictionary of the processing result

        """
        pass


class SWHDeleteDepositAPI(SWHBaseDeposit, metaclass=ABCMeta):
    """Mixin for class to support DELETE method.

    """
    def delete(self, req, collection_name, deposit_id):
        """Endpoint to delete some deposit's resources (archives, deposit).

        Returns:
            204 response when no error during routine occurred.
            400 if the deposit does not belong to the collection
            404 if the deposit or the collection does not exist

        """
        checks = self.checks(req, collection_name, deposit_id)
        if 'error' in checks:
            return make_error_response_from_dict(req, checks['error'])

        data = self.process_delete(req, collection_name, deposit_id)
        error = data.get('error')
        if error:
            return make_error_response_from_dict(req, error)

        return HttpResponse(status=status.HTTP_204_NO_CONTENT)

    @abstractmethod
    def process_delete(self, req, collection_name, deposit_id):
        """Routine to delete a resource.

        This is mostly not allowed except for the
        EM_IRI (cf. .api.deposit_update.SWHUpdateArchiveDeposit)

        """
        pass
