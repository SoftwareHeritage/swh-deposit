# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import datetime
import os
import tempfile

from swh.model import hashutil
from swh.loader.tar import loader
from swh.loader.core.loader import SWHLoader

from .client import DepositClient


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
    CONFIG_BASE_FILENAME = 'loader/deposit'

    ADDITIONAL_CONFIG = {
        'extraction_dir': ('str', '/tmp/swh.deposit.loader/'),
    }

    def __init__(self, client=None):
        super().__init__(
            logging_class='swh.deposit.loader.loader.DepositLoader')
        self.client = client if client else DepositClient()

    def load(self, *, archive_url, deposit_meta_url, deposit_update_url):
        SWHLoader.load(
            self,
            archive_url=archive_url,
            deposit_meta_url=deposit_meta_url,
            deposit_update_url=deposit_update_url)

    def prepare(self, *, archive_url, deposit_meta_url, deposit_update_url):
        """Prepare the loading by first retrieving the deposit's raw archive
           content.

        """
        self.deposit_update_url = deposit_update_url
        temporary_directory = tempfile.TemporaryDirectory()
        self.temporary_directory = temporary_directory
        archive_path = os.path.join(temporary_directory.name, 'archive.zip')
        archive = self.client.archive_get(
            archive_url, archive_path, log=self.log)

        metadata = self.client.metadata_get(
            deposit_meta_url, log=self.log)
        origin = metadata['origin']
        visit_date = datetime.datetime.now(tz=datetime.timezone.utc)
        revision = metadata['revision']
        occurrence = metadata['occurrence']
        self.origin_metadata = metadata['origin_metadata']
        self.prepare_metadata()

        self.client.status_update(deposit_update_url, 'loading')

        super().prepare(tar_path=archive,
                        origin=origin,
                        visit_date=visit_date,
                        revision=revision,
                        occurrences=[occurrence])

    def store_metadata(self):
        """Storing the origin_metadata during the load processus.

        Provider_id and tool_id are resolved during the prepare() method.

        """
        origin_id = self.origin_id
        visit_date = self.visit_date
        provider_id = self.origin_metadata['provider']['provider_id']
        tool_id = self.origin_metadata['tool']['tool_id']
        metadata = self.origin_metadata['metadata']
        try:
            self.send_origin_metadata(origin_id, visit_date, provider_id,
                                      tool_id, metadata)
        except:
            self.log.exception('Problem when storing origin_metadata')
            raise

    def post_load(self, success=True):
        """Updating the deposit's status according to its loading status.

        If not successful, we update its status to failure.
        Otherwise, we update its status to 'success' and pass along
        its associated revision.

        """
        try:
            if not success:
                self.client.status_update(self.deposit_update_url,
                                          status='failure')
                return
            # first retrieve the new revision
            [rev_id] = self.objects['revision'].keys()
            if rev_id:
                rev_id_hex = hashutil.hash_to_hex(rev_id)
                # then update the deposit's status to success with its
                # revision-id
                self.client.status_update(self.deposit_update_url,
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