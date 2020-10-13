# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from swh.deposit.api.checks import check_metadata


@pytest.mark.parametrize(
    "metadata_ok",
    [
        {
            "url": "something",
            "external_identifier": "something-else",
            "name": "foo",
            "author": "someone",
        },
        {
            "url": "some url",
            "external_identifier": "some id",
            "title": "bar",
            "author": "no one",
        },
    ],
)
def test_api_checks_check_metadata_ok(metadata_ok, swh_checks_deposit):
    actual_check, detail = check_metadata(metadata_ok)
    assert actual_check is True
    assert detail is None


@pytest.mark.parametrize(
    "metadata_ko,expected_summary",
    [
        (
            {
                "url": "something",
                "external_identifier": "something-else",
                "author": "someone",
            },
            {
                "summary": "Mandatory alternate fields are missing",
                "fields": ["name or title"],
            },
        ),
        (
            {
                "url": "something",
                "external_identifier": "something-else",
                "title": "foobar",
            },
            {"summary": "Mandatory fields are missing", "fields": ["author"],},
        ),
    ],
)
def test_api_checks_check_metadata_ko(
    metadata_ko, expected_summary, swh_checks_deposit
):
    """Missing optional field should be caught

    """
    actual_check, error_detail = check_metadata(metadata_ko)
    assert actual_check is False
    assert error_detail == {"metadata": [expected_summary]}
