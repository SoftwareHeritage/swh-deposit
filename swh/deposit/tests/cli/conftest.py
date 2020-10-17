# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from click.testing import CliRunner
import pytest


@pytest.fixture
def cli_runner():
    return CliRunner()
