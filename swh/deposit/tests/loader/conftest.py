# Copyright (C) 2019-2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest


@pytest.fixture
def deposit_config(deposit_config):
    return {
        **deposit_config,
        "deposit": {
            "url": "https://deposit.softwareheritage.org/1/private/",
            "auth": {},
        },
    }
