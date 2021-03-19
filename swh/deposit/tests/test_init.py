# Copyright (C) 2020-2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.deposit.api.common import APIBase


def test_version():
    from swh.deposit import __version__

    assert __version__ is not None


@pytest.fixture
def deposit_config(common_deposit_config):
    assert "authentication_provider" not in common_deposit_config
    return common_deposit_config


def test_api_base_misconfigured():
    """No authentication_provider key in configuration should raise"""
    with pytest.raises(ValueError, match="authentication_provider"):
        APIBase()
