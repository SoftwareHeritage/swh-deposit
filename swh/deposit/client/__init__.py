# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of defining an swh-deposit client

"""

import hashlib
import os
import requests

from abc import ABCMeta, abstractmethod
from lxml import etree

from swh.core.config import SWHConfig


class BaseApiDepositClient(SWHConfig):
    """Deposit client base class

    """
    CONFIG_BASE_FILENAME = 'deposit/client'
    DEFAULT_CONFIG = {
        'url': ('str', 'http://localhost:5006'),
        'auth': ('dict', {}),  # with optional 'username'/'password' keys
    }

    def __init__(self, config=None, _client=requests):
        super().__init__()
        if config is None:
            self.config = super().parse_config_file()
        else:
            self.config = config

        self._client = _client
        self.base_url = self.config['url']
        auth = self.config['auth']
        if auth == {}:
            self.auth = None
        else:
            self.auth = (auth['username'], auth['password'])

    def do(self, method, url, *args, **kwargs):
        """Internal method to deal with requests, possibly with basic http
           authentication.

        Args:
            method (str): supported http methods as in self._methods' keys

        Returns:
            The request's execution

        """
        if hasattr(self._client, method):
            method_fn = getattr(self._client, method)
        else:
            raise ValueError('Development error, unsupported method %s' % (
                method))

        if self.auth:
            kwargs['auth'] = self.auth

        full_url = '%s%s' % (self.base_url.rstrip('/'), url)
        return method_fn(full_url, *args, **kwargs)


class ApiDepositClient(BaseApiDepositClient):
    """Private API deposit client to:

    - read a given deposit's archive(s)
    - read a given deposit's metadata
    - update a given deposit's status

    """
    def archive_get(self, archive_update_url, archive_path, log=None):
        """Retrieve the archive from the deposit to a local directory.

        Args:
            archive_update_url (str): The full deposit archive(s)'s raw content
                               to retrieve locally

            archive_path (str): the local archive's path where to store
            the raw content

        Returns:
            The archive path to the local archive to load.
            Or None if any problem arose.

        """
        r = self.do('get', archive_update_url, stream=True)
        if r.ok:
            with open(archive_path, 'wb') as f:
                for chunk in r.iter_content():
                    f.write(chunk)

            return archive_path

        msg = 'Problem when retrieving deposit archive at %s' % (
            archive_update_url, )
        if log:
            log.error(msg)

        raise ValueError(msg)

    def metadata_get(self, metadata_url, log=None):
        """Retrieve the metadata information on a given deposit.

        Args:
            metadata_url (str): The full deposit metadata url to retrieve
            locally

        Returns:
            The dictionary of metadata for that deposit or None if any
            problem arose.

        """
        r = self.do('get', metadata_url)
        if r.ok:
            return r.json()

        msg = 'Problem when retrieving metadata at %s' % metadata_url
        if log:
            log.error(msg)

        raise ValueError(msg)

    def status_update(self, update_status_url, status,
                      revision_id=None):
        """Update the deposit's status.

        Args:
            update_status_url (str): the full deposit's archive
            status (str): The status to update the deposit with
            revision_id (str/None): the revision's identifier to update to

        """
        payload = {'status': status}
        if revision_id:
            payload['revision_id'] = revision_id

        self.do('put', update_status_url, json=payload)

    def check(self, check_url, log=None):
        """Check the deposit's associated data (metadata, archive(s))

        Args:
            check_url (str): the full deposit's check url

        """
        r = self.do('get', check_url)
        if r.ok:
            data = r.json()
            return data['status']

        msg = 'Problem when checking deposit %s' % check_url
        if log:
            log.error(msg)

        raise ValueError(msg)


class BaseDepositClient(BaseApiDepositClient, metaclass=ABCMeta):
    """Base Deposit client to access the public api.

    """
    def __init__(self, config, error_msg=None, empty_result={}):
        super().__init__(config)
        self.error_msg = error_msg
        self.empty_result = empty_result

    @abstractmethod
    def compute_url(self, *args, **kwargs):
        """Compute api url endpoint to query."""
        pass

    @abstractmethod
    def compute_method(self, *args, **kwargs):
        """Http method to use on the url"""
        pass

    @abstractmethod
    def parse_result_ok(self, xml_content):
        """Given an xml result from the api endpoint, parse it and returns a
           dict.

        """
        pass

    def compute_information(self, *args, **kwargs):
        """Compute some more information given the inputs (e.g http headers,
           ...)

        """
        return {}

    def parse_result_error(self, xml_content):
        """Given an error response in xml, parse it into a dict.

        Returns:
            dict with following keys:

                'error': The error message
                'detail': Some more detail about the error if any

        """
        tree = etree.fromstring(xml_content.encode('utf-8'))
        vals = tree.xpath('/x:error/y:summary', namespaces={
            'x': 'http://purl.org/net/sword/',
            'y': 'http://www.w3.org/2005/Atom'
        })
        summary = vals[0].text
        if summary:
            summary = summary.strip()

        vals = tree.xpath(
            '/x:error/x:verboseDescription',
            namespaces={'x': 'http://purl.org/net/sword/'})
        if vals:
            detail = vals[0].text.strip()
        else:
            detail = None

        return {'error': summary, 'detail': detail}

    def do_execute(self, method, url, info):
        """Execute the http query to url using method and info information.

        By default, execute a simple query to url with the http
        method.  Override this in daughter class to improve the
        default behavior if needed.

        """
        return self.do(method, url)

    def execute(self, *args, **kwargs):
        """Main endpoint to prepare and execute the http query to the api.

        """
        url = self.compute_url(*args, **kwargs)
        method = self.compute_method(*args, **kwargs)
        info = self.compute_information(*args, **kwargs)

        try:
            r = self.do_execute(method, url, info)
        except Exception as e:
            msg = self.error_msg % (url, e)
            r = self.empty_result
            r.update({
                'error': msg,
            })
            return r
        else:
            if r.ok:
                if int(r.status_code) == 204:  # 204 returns no body
                    return {'status': r.status_code}
                else:
                    return self.parse_result_ok(r.text)
            else:
                error = self.parse_result_error(r.text)
                empty = self.empty_result
                error.update(empty)
                error.update({
                    'status': r.status_code,
                })
                return error


class ServiceDocumentDepositClient(BaseDepositClient):
    """Service Document information retrieval.

    """
    def __init__(self, config):
        super().__init__(config,
                         error_msg='Service document failure at %s: %s',
                         empty_result={'collection': None})

    def compute_url(self, *args, **kwargs):
        return '/servicedocument/'

    def compute_method(self, *args, **kwargs):
        return 'get'

    def parse_result_ok(self, xml_content):
        """Parse service document's success response.

        """
        tree = etree.fromstring(xml_content.encode('utf-8'))
        collections = tree.xpath(
            '/x:service/x:workspace/x:collection/y:name',
            namespaces={'x': 'http://www.w3.org/2007/app',
                        'y': 'http://purl.org/net/sword/terms/'})
        if collections:
            collection = collections[0].text
        else:
            collection = None

        return {
            'collection': collection
        }


class StatusDepositClient(BaseDepositClient):
    """Status information on a deposit.

    """
    def __init__(self, config):
        super().__init__(config,
                         error_msg='Status check failure at %s: %s',
                         empty_result={
                             'deposit_status': None,
                             'deposit_status_detail': None,
                             'deposit_swh_id': None,
                         })

    def compute_url(self, collection, deposit_id):
        return '/%s/%s/status/' % (collection, deposit_id)

    def compute_method(self, *args, **kwargs):
        return 'get'

    def parse_result_ok(self, xml_content):
        """Given an xml content as string, returns a deposit dict.

        """
        tree = etree.fromstring(xml_content.encode('utf-8'))
        vals = tree.xpath(
            '/x:entry/x:deposit_id',
            namespaces={'x': 'http://www.w3.org/2005/Atom'})
        deposit_id = vals[0].text

        vals = tree.xpath(
            '/x:entry/x:deposit_status',
            namespaces={'x': 'http://www.w3.org/2005/Atom'})
        deposit_status = vals[0].text

        vals = tree.xpath(
            '/x:entry/x:deposit_status_detail',
            namespaces={'x': 'http://www.w3.org/2005/Atom'})
        deposit_status_detail = vals[0].text

        vals = tree.xpath(
            '/x:entry/x:deposit_swh_id',
            namespaces={'x': 'http://www.w3.org/2005/Atom'})
        if vals:
            deposit_swh_id = vals[0].text
        else:
            deposit_swh_id = None

        return {
            'deposit_id': deposit_id,
            'deposit_status': deposit_status,
            'deposit_status_detail': deposit_status_detail,
            'deposit_swh_id': deposit_swh_id,
        }


class BaseCreateDepositClient(BaseDepositClient):
    """Deposit client base class to post new deposit.

    """
    def __init__(self, config):
        super().__init__(config,
                         error_msg='Post Deposit failure at %s: %s',
                         empty_result={
                             'deposit_id': None,
                             'deposit_status': None,
                         })

    def compute_url(self, collection, *args, **kwargs):
        return '/%s/' % collection

    def compute_method(self, *args, **kwargs):
        return 'post'

    def parse_result_ok(self, xml_content):
        """Given an xml content as string, returns a deposit dict.

        """
        tree = etree.fromstring(xml_content.encode('utf-8'))
        vals = tree.xpath(
            '/x:entry/x:deposit_id',
            namespaces={'x': 'http://www.w3.org/2005/Atom'})
        deposit_id = vals[0].text

        vals = tree.xpath(
            '/x:entry/x:deposit_status',
            namespaces={'x': 'http://www.w3.org/2005/Atom'})
        deposit_status = vals[0].text

        vals = tree.xpath(
            '/x:entry/x:deposit_date',
            namespaces={'x': 'http://www.w3.org/2005/Atom'})
        deposit_date = vals[0].text

        return {
            'deposit_id': deposit_id,
            'deposit_status': deposit_status,
            'deposit_date': deposit_date,
        }

    def _compute_information(self, collection, filepath, in_progress, slug,
                             is_archive=True):
        """Given a filepath, compute necessary information on that file.

        Args:
            filepath (str): Path to a file
            is_archive (bool): is it an archive or not?

        Returns:
            dict with keys:
                'content-type': content type associated
                'md5sum': md5 sum
                'filename': filename
        """
        filename = os.path.basename(filepath)

        if is_archive:
            md5sum = hashlib.md5(open(filepath, 'rb').read()).hexdigest()
            extension = filename.split('.')[-1]
            if 'zip' in extension:
                content_type = 'application/zip'
            else:
                content_type = 'application/x-tar'
        else:
            content_type = None
            md5sum = None

        return {
            'slug': slug,
            'in_progress': in_progress,
            'content-type': content_type,
            'md5sum': md5sum,
            'filename': filename,
            'filepath': filepath,
        }

    def compute_information(self, collection, filepath, in_progress, slug,
                            is_archive=True, **kwargs):
        info = self._compute_information(collection, filepath, in_progress,
                                         slug, is_archive=is_archive)
        info['headers'] = self.compute_headers(info)
        return info

    def do_execute(self, method, url, info):
        with open(info['filepath'], 'rb') as f:
            return self.do(method, url, data=f, headers=info['headers'])


class CreateArchiveDepositClient(BaseCreateDepositClient):
    """Post an archive (binary) deposit client."""
    def compute_headers(self, info):
        return {
            'SLUG': info['slug'],
            'CONTENT_MD5': info['md5sum'],
            'IN-PROGRESS': str(info['in_progress']),
            'CONTENT-TYPE': info['content-type'],
            'CONTENT-DISPOSITION': 'attachment; filename=%s' % (
                info['filename'], ),
        }


class UpdateArchiveDepositClient(CreateArchiveDepositClient):
    """Update (add/replace) an archive (binary) deposit client."""
    def compute_url(self, collection, *args, deposit_id=None, **kwargs):
        return '/%s/%s/media/' % (collection, deposit_id)

    def compute_method(self, *args, replace=False, **kwargs):
        return 'put' if replace else 'post'


class CreateMetadataDepositClient(BaseCreateDepositClient):
    """Post a metadata deposit client."""
    def compute_headers(self, info):
        return {
            'SLUG': info['slug'],
            'IN-PROGRESS': str(info['in_progress']),
            'CONTENT-TYPE': 'application/atom+xml;type=entry',
        }


class UpdateMetadataDepositClient(CreateMetadataDepositClient):
    """Update (add/replace) a metadata deposit client."""
    def compute_url(self, collection, *args, deposit_id=None, **kwargs):
        return '/%s/%s/metadata/' % (collection, deposit_id)

    def compute_method(self, *args, replace=False, **kwargs):
        return 'put' if replace else 'post'


class CreateMultipartDepositClient(BaseCreateDepositClient):
    """Create a multipart deposit client."""
    def _multipart_info(self, info, info_meta):
        files = [
            ('file',
             (info['filename'],
              open(info['filepath'], 'rb'),
              info['content-type'])),
            ('atom',
             (info_meta['filename'],
              open(info_meta['filepath'], 'rb'),
              'application/atom+xml')),
        ]

        headers = {
            'SLUG': info['slug'],
            'CONTENT_MD5': info['md5sum'],
            'IN-PROGRESS': str(info['in_progress']),
        }

        return files, headers

    def compute_information(self, collection, archive_path, metadata_path,
                            in_progress, slug, **kwargs):
        info = self._compute_information(
            collection, archive_path, in_progress, slug)
        info_meta = self._compute_information(
            collection, metadata_path, in_progress, slug, is_archive=False)
        files, headers = self._multipart_info(info, info_meta)
        return {'files': files, 'headers': headers}

    def do_execute(self, method, url, info):
        return self.do(
            method, url, files=info['files'], headers=info['headers'])


class UpdateMultipartDepositClient(CreateMultipartDepositClient):
    """Update a multipart deposit client."""
    def compute_url(self, collection, *args, deposit_id=None, **kwargs):
        return '/%s/%s/metadata/' % (collection, deposit_id)

    def compute_method(self, *args, replace=False, **kwargs):
        return 'put' if replace else 'post'


class PublicApiDepositClient(BaseApiDepositClient):
    """Public api deposit client."""
    def service_document(self, log=None):
        """Retrieve service document endpoint's information."""
        return ServiceDocumentDepositClient(self.config).execute()

    def deposit_status(self, collection, deposit_id, log=None):
        """Retrieve status information on a deposit."""
        return StatusDepositClient(self.config).execute(
            collection, deposit_id)

    def deposit_create(self, collection, slug, archive_path=None,
                       metadata_path=None, in_progress=False, log=None):
        """Create a new deposit (archive, metadata, both as multipart)."""
        if archive_path and not metadata_path:
            return CreateArchiveDepositClient(self.config).execute(
                collection, archive_path, in_progress, slug)
        elif not archive_path and metadata_path:
            return CreateMetadataDepositClient(self.config).execute(
                collection, metadata_path, in_progress, slug,
                is_archive=False)
        else:
            return CreateMultipartDepositClient(self.config).execute(
                collection, archive_path, metadata_path, in_progress,
                slug)

    def deposit_update(self, collection, deposit_id, slug, archive_path=None,
                       metadata_path=None, in_progress=False,
                       replace=False, log=None):
        """Update (add/replace) existing deposit (archive, metadata, both)."""
        r = self.deposit_status(collection, deposit_id, log=log)
        if 'error' in r:
            return r

        status = r['deposit_status']
        if status != 'partial':
            return {
                'error': "You can only act on deposit with status 'partial'",
                'detail': "The deposit %s has status '%s'" % (
                    deposit_id, status),
                'deposit_status': status,
                'deposit_id': deposit_id,
            }
        if archive_path and not metadata_path:
            r = UpdateArchiveDepositClient(self.config).execute(
                collection, archive_path, in_progress, slug,
                deposit_id=deposit_id, replace=replace, log=log)
        elif not archive_path and metadata_path:
            r = UpdateMetadataDepositClient(self.config).execute(
                collection, metadata_path, in_progress, slug,
                deposit_id=deposit_id, replace=replace, log=log)
        else:
            r = UpdateMultipartDepositClient(self.config).execute(
                collection, archive_path, metadata_path, in_progress,
                slug, deposit_id=deposit_id, replace=replace, log=log)

        if 'error' in r:
            return r
        return self.deposit_status(collection, deposit_id, log=log)