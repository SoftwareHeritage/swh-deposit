# Copyright (C) 2015-2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.task import Task
from swh.deposit.injection.loader import DepositLoader


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

        Args: see :func:`DepositLoader.load`.

        """
        loader = DepositLoader()
        loader.log = self.log
        loader.load(deposit_archive_url=deposit_archive_url,
                    origin=origin,
                    visit_date=visit_date,
                    revision=revision)