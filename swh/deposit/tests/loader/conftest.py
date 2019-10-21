# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import pytest
import yaml

from swh.scheduler.tests.conftest import *  # noqa
from swh.deposit.loader.checker import DepositChecker


@pytest.fixture(scope='session')
def celery_includes():
    return [
        'swh.deposit.loader.tasks',
    ]


@pytest.fixture
def swh_config(tmp_path, monkeypatch):
    storage_config = {
        'url': 'https://deposit.softwareheritage.org/',
    }

    conffile = os.path.join(tmp_path, 'deposit.yml')
    with open(conffile, 'w') as f:
        f.write(yaml.dump(storage_config))
    monkeypatch.setenv('SWH_CONFIG_FILENAME', conffile)
    return conffile


@pytest.fixture
def deposit_checker(swh_config):
    return DepositChecker()
