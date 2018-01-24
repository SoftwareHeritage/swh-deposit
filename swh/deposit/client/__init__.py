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

    def service_document(self, log=None):
        sd_url = '/servicedocument/'
        try:
            r = self.do('get', sd_url)
        except Exception as e:
            msg = 'Service document failure at %s: %s' % (sd_url, e)
            if log:
                log.error(msg)
            return {
                'collection': None,
                'error': msg,
            }
        else:
            if r.ok:
                tree = etree.fromstring(r.text)
                collections = tree.xpath(
                    '/x:service/x:workspace/x:collection',
                    namespaces={'x': 'http://www.w3.org/2007/app'})
                items = dict(collections[0].items())
                collection = items['href'].rsplit(self.base_url)[1]
                return {
                    'collection': collection
                }
            else:
                return {
                    'collection': None,
                    'error': r.status_code
                }

    def _compute_information_on(self, filepath, is_archive=True):
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
            'content-type': content_type,
            'md5sum': md5sum,
            'filename': filename,
        }

    def _parse_deposit_xml(self, xml_content):
        """Given an xml content as string, returns a deposit dict.

        """
        tree = etree.fromstring(xml_content)
        vals = tree.xpath(
            '/x:entry/x:deposit_id',
            namespaces={'x': 'http://www.w3.org/2005/Atom'})
        deposit_id = vals[0].text

        return {'deposit_id': deposit_id}

    def deposit_binary(self, deposit_url, filepath, slug, in_progress=False,
                       log=None):

        info = self._compute_information_on(filepath)

        headers = {
            'SLUG': slug,
            'CONTENT_MD5': info['md5sum'],
            'IN-PROGRESS': str(in_progress),
            'CONTENT-TYPE': info['content_type'],
            'CONTENT-DISPOSITION': 'attachment; filename=%s' % (
                info['filename'], ),
        }

        try:
            with open(filepath, 'rb') as f:
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
                return {
                    'deposit_id': None,
                    'error': r.status_code
                }

    def deposit_metadata(self, deposit_url, filepath, slug, in_progress,
                         log=None):
        headers = {
            'SLUG': slug,
            'IN-PROGRESS': str(in_progress),
            'CONTENT-TYPE': 'application/atom+xml;type=entry',
        }

        try:
            with open(filepath, 'rb') as f:
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
                return {
                    'deposit_id': None,
                    'error': r.status_code
                }

    def deposit_multipart(self, deposit_url, archive_path, metadata_path,
                          slug, in_progress, log=None):
        info = self._compute_information_on(archive_path)
        info_meta = self._compute_information_on(metadata_path,
                                                 is_archive=False)

        files = [
            ('file',
             (info['filename'],
              open(archive_path, 'rb'),
              info['content-type'])),
            ('atom',
             (info_meta['filename'],
              open(metadata_path, 'rb'),
              'application/atom+xml')),
        ]

        headers = {
            'SLUG': slug,
            'CONTENT_MD5': info['md5sum'],
            'IN-PROGRESS': str(in_progress),
        }

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
                return {
                    'deposit_id': None,
                    'error': r.status_code
                }
