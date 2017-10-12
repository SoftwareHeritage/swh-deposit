# Copyright (C) 2015-2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import requests
import tempfile

from swh.scheduler.task import Task
from swh.loader.tar.loader import TarLoader


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


def update_deposit_status(archive_url, status):
    """Update the deposit's status.

    Args:
        archive_url (str): the full deposit's archive
        status (str): The status to update the deposit with

    """
    update_url = archive_url.replace('/raw/', '/update/')
    requests.put(update_url,
                 json={'status': status})


class LoadDepositArchive(Task):
    """Deposit archive ingestion task described by the following steps:

       1. Retrieve tarball from deposit's private api and store
          locally in a temporary directory
       2. Trigger the ingestion
       3. clean up the temporary directory
       4. Update the deposit's status according to result using the
          deposit's private update status api

    """
    task_queue = 'swh_deposit_archive'

    def run_task(self, *, deposit_archive_url, origin, visit_date,
                 revision):
        """Import a deposit tarball into swh.

        Args: see :func:`TarLoader.load`.

        """
        temporary_directory = tempfile.TemporaryDirectory()
        archive_path = os.path.join(temporary_directory.name, 'archive.zip')
        archive = retrieve_archive_to(deposit_archive_url, archive_path)

        if not archive:
            raise ValueError('Failure to retrieve archive')

        occurrence = {'branch': 'master'}
        try:
            loader = TarLoader()
            loader.log = self.log
            loader.load(tar_path=archive_path,
                        origin=origin,
                        visit_date=visit_date,
                        revision=revision,
                        occurrences=[occurrence])
            status = 'success'
        except:
            self.log.exception('What happened?')
            status = 'failure'

        update_deposit_status(deposit_archive_url, status)
