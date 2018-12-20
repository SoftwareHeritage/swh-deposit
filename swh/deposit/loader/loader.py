# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import tempfile

from swh.model import hashutil
from swh.loader.tar import loader
from swh.loader.core.loader import BufferedLoader

from ..client import PrivateApiDepositClient


class DepositLoader(loader.LegacyLocalTarLoader):
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
        self.deposit_client = client if client else PrivateApiDepositClient()

    def load(self, *, archive_url, deposit_meta_url, deposit_update_url):
        return BufferedLoader.load(
            self,
            archive_url=archive_url,
            deposit_meta_url=deposit_meta_url,
            deposit_update_url=deposit_update_url)

    def prepare_origin_visit(self, *, deposit_meta_url, **kwargs):
        self.metadata = self.deposit_client.metadata_get(
            deposit_meta_url, log=self.log)
        self.origin = self.metadata['origin']
        self.visit_date = None

    def prepare(self, *, archive_url, deposit_meta_url, deposit_update_url):
        """Prepare the loading by first retrieving the deposit's raw archive
           content.

        """
        self.deposit_update_url = deposit_update_url
        self.deposit_client.status_update(deposit_update_url, 'loading')

        temporary_directory = tempfile.TemporaryDirectory()
        self.temporary_directory = temporary_directory
        archive_path = os.path.join(temporary_directory.name, 'archive.zip')
        archive = self.deposit_client.archive_get(
            archive_url, archive_path, log=self.log)

        metadata = self.metadata
        revision = metadata['revision']
        branch_name = metadata['branch_name']
        self.origin_metadata = metadata['origin_metadata']
        self.prepare_metadata()

        super().prepare(tar_path=archive,
                        origin=self.origin,
                        revision=revision,
                        branch_name=branch_name)

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
        except Exception:
            self.log.exception('Problem when storing origin_metadata')
            raise

    def post_load(self, success=True):
        """Updating the deposit's status according to its loading status.

        If not successful, we update its status to 'failed'.
        Otherwise, we update its status to 'done' and pass along its
        associated revision.

        """
        try:
            if not success:
                self.deposit_client.status_update(self.deposit_update_url,
                                                  status='failed')
                return

            revisions = self.objects['revision']
            # Retrieve the revision
            [rev_id] = revisions.keys()
            rev = revisions[rev_id]
            if rev_id:
                rev_id = hashutil.hash_to_hex(rev_id)

            dir_id = rev['directory']
            if dir_id:
                dir_id = hashutil.hash_to_hex(dir_id)

            # update the deposit's status to success with its
            # revision-id and directory-id
            self.deposit_client.status_update(
                self.deposit_update_url,
                status='done',
                revision_id=rev_id,
                directory_id=dir_id,
                origin_url=self.origin['url'])
        except Exception:
            self.log.exception(
                'Problem when trying to update the deposit\'s status')

    def cleanup(self):
        """Clean up temporary directory where we retrieved the tarball.

        """
        super().cleanup()
        self.temporary_directory.cleanup()
