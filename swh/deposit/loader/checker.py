# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

from typing import Mapping

from swh.deposit.client import PrivateApiDepositClient


logger = logging.getLogger(__name__)


class DepositChecker():
    """Deposit checker implementation.

    Trigger deposit's checks through the private api.

    """
    def __init__(self, client=None):
        super().__init__()
        self.client = client if client else PrivateApiDepositClient()

    def check(self, deposit_check_url: str) -> Mapping[str, str]:
        status = None
        try:
            r = self.client.check(deposit_check_url)
            status = 'eventful' if r == 'verified' else 'failed'
        except Exception:
            logger.exception("Failure during check on '%s'" % (
                deposit_check_url, ))
            status = 'failed'
        return {'status': status}
