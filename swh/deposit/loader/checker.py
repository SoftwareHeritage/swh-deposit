# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging


from ..client import PrivateApiDepositClient


class DepositChecker():
    """Deposit checker implementation.

    Trigger deposit's checks through the private api.

    """
    def __init__(self, client=None):
        super().__init__()
        self.client = client if client else PrivateApiDepositClient()
        logging_class = '%s.%s' % (self.__class__.__module__,
                                   self.__class__.__name__)
        self.log = logging.getLogger(logging_class)

    def check(self, deposit_check_url):
        try:
            self.client.check(deposit_check_url)
        except Exception:
            self.log.exception("Failure during check on '%s'" % (
                deposit_check_url, ))
            return {'status': 'failed'}
        else:
            return {'status': 'eventful'}
