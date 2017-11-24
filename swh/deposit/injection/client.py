# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of defining an swh-deposit client

"""

import requests


class DepositClient:
    """Deposit client to:

    - read archive
    - read metadata
    - update deposit's status

    """
    def read_archive_to(self, archive_update_url, archive_path, log=None):
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
        r = requests.get(archive_update_url, stream=True)
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

    def read_metadata(self, metadata_url, log=None):
        """Retrieve the metadata information on a given deposit.

        Args:
            metadata_url (str): The full deposit metadata url to retrieve
            locally

        Returns:
            The dictionary of metadata for that deposit or None if any
            problem arose.

        """
        r = requests.get(metadata_url)
        if r.ok:
            return r.json()

        msg = 'Problem when retrieving metadata at %s' % metadata_url
        if log:
            log.error(msg)

        raise ValueError(msg)

    def update_status(self, update_status_url, status,
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
            requests.put(update_status_url, json=payload)
