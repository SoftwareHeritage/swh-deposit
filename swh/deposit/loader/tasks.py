# Copyright (C) 2015-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from celery import current_app as app

from swh.deposit.loader.loader import DepositLoader
from swh.deposit.loader.checker import DepositChecker


@app.task(name=__name__ + '.LoadDepositArchiveTsk')
def load_deposit_archive(archive_url, deposit_meta_url, deposit_update_url):
    """Deposit archive loading task described by the following steps:

       1. Retrieve tarball from deposit's private api and store
          locally in a temporary directory
       2. Trigger the loading
       3. clean up the temporary directory
       4. Update the deposit's status according to result using the
          deposit's private update status api

    """
    return DepositLoader().load(
        archive_url=archive_url,
        deposit_meta_url=deposit_meta_url,
        deposit_update_url=deposit_update_url)


@app.task(name=__name__ + '.ChecksDepositTsk')
def check_deposit(deposit_check_url):
    """Check a deposit's status

    Args: see :func:`DepositChecker.check`.
    """
    return DepositChecker().check(deposit_check_url)
