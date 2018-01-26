# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of defining an swh-deposit client

"""

import hashlib
import os
import requests

from swh.core.config import SWHConfig
from lxml import etree


class ApiDepositClient(SWHConfig):
    """Deposit client to:

    - read a given deposit's archive(s)
    - read a given deposit's metadata
    - update a given deposit's status

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


class _DepositClient(ApiDepositClient):
    def __init__(self, config, error_msg=None, empty_result={}):
        super().__init__(config)
        self.error_msg = error_msg
        self.empty_result = empty_result

    def compute_url(self, *args, **kwargs):
        pass

    def compute_method(self, *args, **kwargs):
        pass

    def parse_result_ok(self, xml_content):
        pass

    def _parse_result_error(self, xml_content):
        """Parse xml error response to a dict.

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
            detail = vals[0].text
        else:
            detail = None

        return {'error': summary, 'detail': detail}

    def execute(self, *args, **kwargs):
        url = self.compute_url(*args, **kwargs)
        method = self.compute_method(*args, **kwargs)

        try:
            r = self.do(method, url)
        except Exception as e:
            msg = self.error_msg % (url, e)
            r = self.empty_result
            r.update({
                'error': msg,
            })
        else:
            if r.ok:
                return self._parse_result_ok(r.text)
            else:
                error = self._parse_result_error(r.text)
                empty = self.empty_result
                error.update(empty)
                error.update({
                    'status': r.status_code,
                })
                return error


class ServiceDocumentDepositClient(_DepositClient):
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

    def _parse_result_ok(self, xml_content):
        """Parse service document's success response.

        """
        tree = etree.fromstring(xml_content.encode('utf-8'))
        collections = tree.xpath(
            '/x:service/x:workspace/x:collection',
            namespaces={'x': 'http://www.w3.org/2007/app'})
        items = dict(collections[0].items())
        collection = items['href'].rsplit(self.base_url)[1]
        return {
            'collection': collection
        }


class StatusDepositClient(_DepositClient):
    """Status information retrieval.

    """
    def __init__(self, config):
        super().__init__(config,
                         error_msg='Status check failure at %s: %s',
                         empty_result={
                             'deposit_status': None,
                             'deposit_status_detail': None,
                             'deposit_swh_id': None,
                         })

    def compute_url(self, *args, **kwargs):
        collection, deposit_id = args
        return '/%s/%s/status/' % (collection, deposit_id)

    def compute_method(self, *args, **kwargs):
        return 'get'

    def _parse_result_ok(self, xml_content):
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


class PublicApiDepositClient(ApiDepositClient):
    """Public api deposit client.

    """
    def service_document(self, log=None):
        """Retrieve service document endpoint's information.

        """
        return ServiceDocumentDepositClient(self.config).execute()

    def deposit_status(self, collection, deposit_id, log=None):
        return StatusDepositClient(self.config).execute(
            collection, deposit_id)

    def _compute_information(self, filepath, in_progress, slug,
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
        md5sum = hashlib.md5(open(filepath, 'rb').read()).hexdigest()
        filename = os.path.basename(filepath)

        if is_archive:
            extension = filename.split('.')[-1]
            if 'zip' in extension:
                content_type = 'application/zip'
            else:
                content_type = 'application/x-tar'
        else:
            content_type = None

        return {
            'slug': slug,
            'in_progress': in_progress,
            'content-type': content_type,
            'md5sum': md5sum,
            'filename': filename,
            'filepath': filepath,
        }

    def _parse_deposit_xml(self, xml_content):
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

    def _parse_deposit_error(self, xml_content):
        """Parse xml error response to a dict.

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

    def _compute_deposit_url(self, collection):
        return '/%s/' % collection

    def _compute_binary_url(self, collection, deposit_id):
        return '/%s/%s/media/' % (collection, deposit_id)

    def _compute_metadata_url(self, collection, deposit_id):
        return '/%s/%s/metadata/' % (collection, deposit_id)

    def _compute_multipart_url(self, collection, deposit_id):
        return self._compute_metadata_url(collection, deposit_id)

    def deposit_create(self, collection, slug, archive_path=None,
                       metadata_path=None, in_progress=False, log=None):
        """Create a new deposit.

        """
        if archive_path and not metadata_path:
            return self.deposit_binary(collection, archive_path, slug,
                                       in_progress, log)
        elif not archive_path and metadata_path:
            return self.deposit_metadata(collection, metadata_path, slug,
                                         in_progress, log)
        else:
            return self.deposit_multipart(collection, archive_path,
                                          metadata_path, slug, in_progress,
                                          log)

    def _binary_headers(self, info):
        return {
            'SLUG': info['slug'],
            'CONTENT_MD5': info['md5sum'],
            'IN-PROGRESS': str(info['in_progress']),
            'CONTENT-TYPE': info['content-type'],
            'CONTENT-DISPOSITION': 'attachment; filename=%s' % (
                info['filename'], ),
        }

    def deposit_binary(self, collection, archive_path, slug,
                       in_progress=False, log=None):
        deposit_url = self._compute_deposit_url(collection)
        info = self._compute_information(archive_path, in_progress, slug)
        headers = self._binary_headers(info)

        try:
            with open(archive_path, 'rb') as f:
                r = self.do('post', deposit_url, data=f, headers=headers)

        except Exception as e:
            msg = 'Binary posting deposit failure at %s: %s' % (deposit_url, e)
            if log:
                log.error(msg)

            return {
                'deposit_id': None,
                'error': msg,
            }
        else:
            if r.ok:
                return self._parse_deposit_xml(r.text)
            else:
                error = self._parse_deposit_error(r.text)
                error.update({
                    'deposit_id': None,
                    'status': r.status_code,
                })
                return error

    def _metadata_headers(self, info):
        return {
            'SLUG': info['slug'],
            'IN-PROGRESS': str(info['in_progress']),
            'CONTENT-TYPE': 'application/atom+xml;type=entry',
        }

    def deposit_metadata(self, collection, metadata_path, slug, in_progress,
                         log=None):
        deposit_url = self._compute_deposit_url(collection)
        headers = self._metadata_headers(
            {'slug': slug, 'in_progress': in_progress})

        try:
            with open(metadata_path, 'rb') as f:
                r = self.do('post', deposit_url, data=f, headers=headers)

        except Exception as e:
            msg = 'Metadata posting deposit failure at %s: %s' % (
                deposit_url, e)
            if log:
                log.error(msg)

            return {
                'deposit_id': None,
                'error': msg,
            }
        else:
            if r.ok:
                return self._parse_deposit_xml(r.text)
            else:
                error = self._parse_deposit_error(r.text)
                error.update({
                    'deposit_id': None,
                    'status': r.status_code,
                })
                return error

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

    def deposit_multipart(self, collection, archive_path, metadata_path,
                          slug, in_progress, log=None):
        deposit_url = self._compute_deposit_url(collection)
        info = self._compute_information(archive_path, in_progress, slug)
        info_meta = self._compute_information(
            metadata_path, in_progress, slug, is_archive=False)
        files, headers = self._multipart_info(info, info_meta)

        try:
            r = self.do('post', deposit_url, files=files, headers=headers)
        except Exception as e:
            msg = 'Multipart posting deposit failure at %s: %s' % (
                deposit_url, e)
            if log:
                log.error(msg)

            return {
                'deposit_id': None,
                'error': msg,
            }
        else:
            if r.ok:
                return self._parse_deposit_xml(r.text)
            else:
                error = self._parse_deposit_error(r.text)
                error.update({
                    'deposit_id': None,
                    'status': r.status_code,
                })
                return error

    # replace   PUT    EM    binary
    # !replace  POST   EM    binary
    # replace   PUT    EDIT  multipart ; atom
    # !replace  POST   EDIT  multipart ; atom

    def deposit_update(self, collection, deposit_id, slug, archive_path=None,
                       metadata_path=None, in_progress=False,
                       replace=False, log=None):
        """Update an existing deposit.

        """
        if archive_path and not metadata_path:
            return self.deposit_binary_update(
                collection, deposit_id, archive_path, slug,
                in_progress, replace, log)
        elif not archive_path and metadata_path:
            return self.deposit_metadata_update(
                collection, deposit_id, metadata_path, slug,
                in_progress, replace, log)
        else:
            return self.deposit_multipart_update(
                collection, deposit_id, archive_path, metadata_path, slug,
                in_progress, replace, log)

    def deposit_binary_update(self, collection, deposit_id, archive_path,
                              slug, in_progress, replace, log=None):
        method = 'put' if replace else 'post'
        deposit_url = self._compute_binary_url(collection, deposit_id)

        info = self._compute_information(archive_path, in_progress, slug)
        headers = self._binary_headers(info)

        try:
            with open(archive_path, 'rb') as f:
                r = self.do(method, deposit_url, data=f, headers=headers)

        except Exception as e:
            msg = 'Binary deposit updating failure at %s: %s' % (
                deposit_url, e)
            if log:
                log.error(msg)

            return {
                'deposit_id': None,
                'error': msg,
            }
        else:
            if r.ok:
                return self._parse_deposit_xml(r.text)
            else:
                error = self._parse_deposit_error(r.text)
                error.update({
                    'deposit_id': None,
                    'status': r.status_code,
                })
                return error

    def deposit_metadata_update(self, collection, deposit_id, metadata_path,
                                slug, in_progress, replace, log=None):
        method = 'put' if replace else 'post'
        deposit_url = self._compute_metadata_url(collection, deposit_id)
        headers = self._metadata_headers(
            {'slug': slug, 'in_progress': in_progress})

        try:
            with open(metadata_path, 'rb') as f:
                r = self.do(method, deposit_url, data=f, headers=headers)

        except Exception as e:
            msg = 'Metadata deposit updating deposit failure at %s: %s' % (
                deposit_url, e)
            if log:
                log.error(msg)

            return {
                'deposit_id': None,
                'error': msg,
            }
        else:
            if r.ok:
                return self._parse_deposit_xml(r.text)
            else:
                error = self._parse_deposit_error(r.text)
                error.update({
                    'deposit_id': None,
                    'status': r.status_code,
                })
                return error

    def deposit_multipart_update(self, collection, deposit_id, archive_path,
                                 metadata_path, slug, in_progress, replace,
                                 log=None):
        method = 'put' if replace else 'post'
        deposit_url = self._compute_multipart_url(collection, deposit_id)
        info = self._compute_information(archive_path, in_progress, slug)
        info_meta = self._compute_information(metadata_path, in_progress, slug,
                                              is_archive=False)
        files, headers = self._multipart_info(info, info_meta)

        try:
            r = self.do(method, deposit_url, files=files, headers=headers)
        except Exception as e:
            msg = 'Multipart deposit updating failure at %s: %s' % (
                deposit_url, e)
            if log:
                log.error(msg)

            return {
                'deposit_id': None,
                'error': msg,
            }
        else:
            if r.ok:
                return self._parse_deposit_xml(r.text)
            else:
                error = self._parse_deposit_error(r.text)
                error.update({
                    'deposit_id': None,
                    'status': r.status_code,
                })
                return error
