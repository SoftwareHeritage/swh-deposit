# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os

import pytest

from swh.deposit.config import setup_django_for


def test_setup_django_for_raise_unknown_platform():
    """Unknown platform should make the function setup raise"""
    with pytest.raises(ValueError, match="Platform should be"):
        setup_django_for(platform="unknown")


def test_setup_django__for_set_django_settings_module(monkeypatch, deposit_config_path):
    monkeypatch.delenv("DJANGO_SETTINGS_MODULE")
    platform = "testing"
    setup_django_for(platform)

    assert os.environ["DJANGO_SETTINGS_MODULE"] == f"swh.deposit.settings.{platform}"


def test_setup_django_for_ok_set_django_settings_module(
    monkeypatch, deposit_config_path
):
    monkeypatch.delenv("SWH_CONFIG_FILENAME")
    setup_django_for("testing", deposit_config_path)

    assert os.environ["SWH_CONFIG_FILENAME"] == deposit_config_path


def test_setup_django_for_ok(deposit_config_path):
    """Everything is fine, moving along (fixture sets environment appropriately)"""
    setup_django_for()
