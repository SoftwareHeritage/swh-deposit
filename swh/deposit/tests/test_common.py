# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.deposit.tests.common import check_archive


def test_check_archive_helper():
    # success
    for archive_name, archive_name_to_check in [
        ("filename0", "something/filename0"),
        ("archive.zip", "client_1/archive_noisynoise.zip"),
    ]:
        check_archive(archive_name, archive_name_to_check)

    # failures
    for archive_name, archive_name_to_check in [
        ("filename0", "something-filename0"),
        ("archive.zip", "client_1_archive_noisynoise.zip"),
        ("reference", "irrelevant"),
    ]:
        with pytest.raises(AssertionError):
            check_archive(archive_name, archive_name_to_check)
