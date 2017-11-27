# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of defining a swh-deposit client

"""

import requests
from swh.core.config import SWHConfig


class DepositClient(SWHConfig):
    """Deposit client to:

    - read archive
    - read metadata
    - update deposit's status

    """
    CONFIG_BASE_FILENAME = 'deposit/client'
    DEFAULT_CONFIG = {}

    def __init__(self, config=None, _client=requests):
        if config is not None:
            self.config = config
        else:
            super().__init__()

        self._client = _client

        if 'username' in self.config and 'password' in self.config:
            self.auth = (self.config['username'], self.config['password'])
        else:
            self.auth = None

    def do(self, method, *args, **kwargs):
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

        return method_fn(*args, **kwargs)

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
