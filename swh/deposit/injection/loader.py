# Copyright (C) 2015-2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import datetime
import os
import requests
import tempfile

from swh.model import hashutil
from swh.loader.tar import loader
from swh.loader.core.loader import SWHLoader


class DepositClient:
    """Deposit client to read archive, metadata or update deposit's status.

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
            data = r.json()

            return data

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


class DepositLoader(loader.TarLoader):
    """Deposit loader implementation.

    This is a subclass of the :class:TarLoader as the main goal of
    this class is to first retrieve the deposit's tarball contents as
    one and its associated metadata. Then provide said tarball to be
    loaded by the TarLoader.

    This will:

    - retrieves the deposit's archive locally
    - provide the archive to be loaded by the tar loader
    - clean up the temporary location used to retrieve the archive locally
    - update the deposit's status accordingly

    """
    def __init__(self, client=None):
        super().__init__()
        if client:
            self.client = client
        else:
            self.client = DepositClient()

    def load(self, *, archive_url, deposit_meta_url, deposit_update_url):
        SWHLoader.load(
            self,
            archive_url=archive_url,
            deposit_meta_url=deposit_meta_url,
            deposit_update_url=deposit_update_url)

    def prepare(self, *, archive_url, deposit_meta_url, deposit_update_url):
        """Prepare the injection by first retrieving the deposit's raw archive
           content.

        """
        self.deposit_update_url = deposit_update_url
        temporary_directory = tempfile.TemporaryDirectory()
        self.temporary_directory = temporary_directory
        archive_path = os.path.join(temporary_directory.name, 'archive.zip')
        archive = self.client.get_archive(
            archive_url, archive_path, log=self.log)

        metadata = self.client.get_metadata(
            deposit_meta_url, log=self.log)
        origin = metadata['origin']
        visit_date = datetime.datetime.now(tz=datetime.timezone.utc)
        revision = metadata['revision']
        occurrence = metadata['occurrence']

        self.client.update_deposit_status(deposit_update_url, 'injecting')

        super().prepare(tar_path=archive,
                        origin=origin,
                        visit_date=visit_date,
                        revision=revision,
                        occurrences=[occurrence])

    def store_metadata(self):
        """Storing the origin_metadata during the load processus.

        Fetching tool and metadata_provider from storage and adding the
        metadata associated to the current origin.

        """
        origin_id = self.origin_id
        visit_date = self.visit_date
        provider = self.origin_metadata['provider']
        tool = self.origin_metadata['tool']
        metadata = self.origin_metadata['metadata']
        try:
            self.send_origin_metadata(self, origin_id, visit_date, provider,
                                      tool, metadata)
        except:
            self.log.exception('Problem when storing origin_metadata')

    def post_load(self, success=True):
        """Updating the deposit's status according to its loading status.

        If not successful, we update its status to failure.
        Otherwise, we update its status to 'success' and pass along
        its associated revision.

        """
        try:
            if not success:
                self.client.update_deposit_status(self.deposit_update_url,
                                                  status='failure')
                return
            # first retrieve the new revision
            [rev_id] = self.objects['revision'].keys()
            if rev_id:
                rev_id_hex = hashutil.hash_to_hex(rev_id)
                # then update the deposit's status to success with its
                # revision-id
                self.client.update_deposit_status(self.deposit_update_url,
                                                  status='success',
                                                  revision_id=rev_id_hex)
        except:
            self.log.exception(
                'Problem when trying to update the deposit\'s status')

    def cleanup(self):
        """Clean up temporary directory where we retrieved the tarball.

        """
        super().cleanup()
        self.temporary_directory.cleanup()
