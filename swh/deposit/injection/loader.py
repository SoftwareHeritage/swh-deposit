# Copyright (C) 2015-2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import requests
import tempfile


from swh.model import hashutil
from swh.loader.tar import loader
from swh.loader.core.loader import SWHLoader


def retrieve_archive_to(archive_url, archive_path):
    """Retrieve the archive from the deposit to a local directory.

    Args:

        archive_url (str): The full deposit archive(s)'s raw content
                           to retrieve locally

        archive_path (str): the local archive's path where to store
        the raw content

    Returns:
        The archive path to the local archive to load.
        Or None if any problem arose.

    """
    r = requests.get(archive_url, stream=True)
    if r.ok:
        with open(archive_path, 'wb') as f:
            for chunk in r.iter_content():
                f.write(chunk)

        return archive_path
    return None


def update_deposit_status(archive_url, status, revision_id=None):
    """Update the deposit's status.

    Args:
        archive_url (str): the full deposit's archive
        status (str): The status to update the deposit with
        revision_id (str/None): the revision's identifier to update to

    """
    update_url = archive_url.replace('/raw/', '/update/')
    payload = {'status': status}
    if revision_id:
        payload['revision_id'] = revision_id
    requests.put(update_url, json=payload)


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
    def load(self, *, deposit_archive_url, origin, visit_date, revision):
        occurrence = {'branch': 'master'}
        SWHLoader.load(self,
                       deposit_archive_url=deposit_archive_url,
                       origin=origin,
                       visit_date=visit_date,
                       revision=revision,
                       occurrences=[occurrence])

    def prepare(self, *, deposit_archive_url, origin, visit_date, revision,
                occurrences):
        """Prepare the injection by first retrieving the deposit's raw archive
           content.

        """
        self.archive_url = deposit_archive_url
        temporary_directory = tempfile.TemporaryDirectory()
        self.temporary_directory = temporary_directory
        archive_path = os.path.join(temporary_directory.name, 'archive.zip')
        archive = retrieve_archive_to(deposit_archive_url, archive_path)

        if not archive:
            raise ValueError('Failure to retrieve archive')

        update_deposit_status(self.archive_url, 'injecting')
        super().prepare(tar_path=archive,
                        origin=origin,
                        visit_date=visit_date,
                        revision=revision,
                        occurrences=occurrences)

    def post_load(self, success=True):
        """Updating the deposit's status according to its loading status.

        If not successful, we update its status to failure.
        Otherwise, we update its status to 'success' and pass along
        its associated revision.

        """
        try:
            if not success:
                update_deposit_status(self.archive_url, status='failure')
                return
            # first retrieve the new revision
            occs = list(self.storage.occurrence_get(self.origin_id))
            if occs:
                occ = occs[0]
                revision_id = hashutil.hash_to_hex(occ['target'])
                # then update the deposit's status to success with its
                # revision-id
                update_deposit_status(self.archive_url,
                                      status='success',
                                      revision_id=revision_id)
        except:
            self.log.exception(
                'Problem when trying to update the deposit\'s status')

    def cleanup(self):
        """Clean up temporary directory where we retrieved the tarball.

        """
        super().cleanup()
        self.temporary_directory.cleanup()
