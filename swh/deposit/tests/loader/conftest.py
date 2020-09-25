# Copyright (C) 2019-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from functools import partial
import re

import pytest

from swh.core.pytest_plugin import get_response_cb
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


@pytest.fixture
def requests_mock_datadir(datadir, requests_mock_datadir):
    """Override default behavior to deal with put method

    """
    cb = partial(get_response_cb, datadir=datadir)
    requests_mock_datadir.put(re.compile("https://"), body=cb)
    return requests_mock_datadir
