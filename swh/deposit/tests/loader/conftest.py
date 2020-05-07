# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import re
import os
import pytest
import yaml

from functools import partial

from swh.core.pytest_plugin import get_response_cb
from swh.scheduler.tests.conftest import *  # noqa
from swh.storage.tests.conftest import *  # noqa
from swh.deposit.loader.checker import DepositChecker


@pytest.fixture(scope="session")  # type: ignore  # expected redefinition
def celery_includes():
    return [
        "swh.deposit.loader.tasks",
    ]


@pytest.fixture
def swh_config(tmp_path, swh_storage_postgresql, monkeypatch):
    storage_config = {
        "url": "https://deposit.softwareheritage.org/",
        "storage": {
            "cls": "local",
            "args": {
                "db": swh_storage_postgresql.dsn,
                "objstorage": {"cls": "memory", "args": {}},
            },
        },
    }

    conffile = os.path.join(tmp_path, "deposit.yml")
    with open(conffile, "w") as f:
        f.write(yaml.dump(storage_config))
    monkeypatch.setenv("SWH_CONFIG_FILENAME", conffile)
    return conffile


@pytest.fixture
def deposit_checker():
    return DepositChecker(
        config={
            "deposit": {
                "url": "https://deposit.softwareheritage.org/1/private/",
                "auth": {},
            }
        }
    )


@pytest.fixture
def requests_mock_datadir(datadir, requests_mock_datadir):
    """Override default behavior to deal with put method

    """
    cb = partial(get_response_cb, datadir=datadir)
    requests_mock_datadir.put(re.compile("https://"), body=cb)
    return requests_mock_datadir
