# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.deposit.loader.checker import DepositChecker


@pytest.fixture
def deposit_config(tmp_path):
    return {
        "deposit": {
            "url": "https://deposit.softwareheritage.org/1/private/",
            "auth": {},
        }
    }


@pytest.fixture
def deposit_checker(deposit_config_path):
    return DepositChecker()
