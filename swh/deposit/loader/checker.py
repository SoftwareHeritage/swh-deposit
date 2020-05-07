# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

from typing import Mapping

from swh.core.config import SWHConfig

from swh.deposit.client import PrivateApiDepositClient


logger = logging.getLogger(__name__)


class DepositChecker(SWHConfig):
    """Deposit checker implementation.

    Trigger deposit's checks through the private api.

    """

    CONFIG_BASE_FILENAME = "deposit/checker"

    DEFAULT_CONFIG = {
        "deposit": ("dict", {"url": "http://localhost:5006/1/private/", "auth": {},})
    }

    def __init__(self, config=None):
        super().__init__()
        if config is None:
            self.config = self.parse_config_file()
        else:
            self.config = config
        self.client = PrivateApiDepositClient(config=self.config["deposit"])

    def check(self, collection: str, deposit_id: str) -> Mapping[str, str]:
        status = None
        deposit_check_url = f"/{collection}/{deposit_id}/check/"
        logger.debug("deposit-check-url: %s", deposit_check_url)
        try:
            r = self.client.check(deposit_check_url)
            logger.debug("Check result: %s", r)
            status = "eventful" if r == "verified" else "failed"
        except Exception:
            logger.exception("Failure during check on '%s'", deposit_check_url)
            status = "failed"
        logger.debug("Check status: %s", status)
        return {"status": status}
