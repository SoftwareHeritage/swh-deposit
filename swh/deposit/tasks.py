# Copyright (C) 2015-2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.task import Task

from swh.loader.tar.loader import TarLoader


def fetch_archive_locally(archive_url):
    pass


class LoadDepositArchive(Task):
    task_queue = 'swh_deposit_archive'

    def run_task(self, *, deposit_archive_url, origin, visit_date,
                 revision):
        """Import a deposit tarball into swh.

        Args: see :func:`TarLoader.load`.

        """
        loader = TarLoader()
        loader.log = self.log

        # FIXME: Retrieve tarball and copy locally

        tar_path = 'foobar'

        import os
        occurrence = os.path.basename(tar_path)

        self.log.info('%s %s %s %s %s' % (deposit_archive_url, origin,
                                          visit_date, revision,
                                          [occurrence]))
        # loader.load(tar_path=tar_path, origin=origin, visit_date=visit_date,
        #             revision=revision, occurrences=[occurrence])
