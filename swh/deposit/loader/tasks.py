# Copyright (C) 2015-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Mapping

from celery import shared_task

from swh.deposit.loader.checker import DepositChecker


@shared_task(name=__name__ + ".ChecksDepositTsk")
def check_deposit(collection: str, deposit_id: str) -> Mapping[str, str]:
    """Check a deposit's status

    Args: see :func:`DepositChecker.check`.
    """
    checker = DepositChecker()
    return checker.check(collection, deposit_id)
