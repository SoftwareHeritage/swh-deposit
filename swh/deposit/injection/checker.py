# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from .client import DepositClient


class DepositChecker():
    """Deposit checker implementation.

    Trigger deposit's checks through the private api.

    """
    def __init__(self, client=None):
        super().__init__()
        if client:
            self.client = client
        else:
            self.client = DepositClient()

    def check(self, deposit_check_url):
        self.client.get(deposit_check_url)
