# Copyright (C) 2015-2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.scheduler.task import Task
from swh.deposit.injection.loader import DepositLoader
from swh.deposit.injection.checker import DepositChecker


class LoadDepositArchiveTsk(Task):
    """Deposit archive injection task described by the following steps:

       1. Retrieve tarball from deposit's private api and store
          locally in a temporary directory
       2. Trigger the injection
       3. clean up the temporary directory
       4. Update the deposit's status according to result using the
          deposit's private update status api

    """
    task_queue = 'swh_loader_deposit'

    def run_task(self, *, archive_url, deposit_meta_url, deposit_update_url):
        """Import a deposit tarball into swh.

        Args: see :func:`DepositLoader.load`.

        """
        loader = DepositLoader()
        loader.log = self.log
        loader.load(archive_url=archive_url,
                    deposit_meta_url=deposit_meta_url,
                    deposit_update_url=deposit_update_url)


class ChecksDepositTsk(Task):
    """Deposit checks task.

    """
    task_queue = 'swh_checker_deposit'

    def run_task(self, deposit_check_url):
        """Check a deposit's status

        Args: see :func:`DepositChecker.check`.

        """
        checker = DepositChecker()
        checker.log = self.log
        checker.check(deposit_check_url)
