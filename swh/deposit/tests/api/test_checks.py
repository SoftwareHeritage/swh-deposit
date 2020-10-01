# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.deposit.api.checks import check_metadata


def test_api_checks_check_metadata_ok(swh_checks_deposit):
    actual_check, detail = check_metadata(
        {
            "url": "something",
            "external_identifier": "something-else",
            "name": "foo",
            "author": "someone",
        }
    )

    assert actual_check is True
    assert detail is None


def test_api_checks_check_metadata_ok2(swh_checks_deposit):
    actual_check, detail = check_metadata(
        {
            "url": "something",
            "external_identifier": "something-else",
            "title": "bar",
            "author": "someone",
        }
    )

    assert actual_check is True
    assert detail is None


def test_api_checks_check_metadata_ko(swh_checks_deposit):
    """Missing optional field should be caught

    """
    actual_check, error_detail = check_metadata(
        {
            "url": "something",
            "external_identifier": "something-else",
            "author": "someone",
        }
    )

    expected_error = {
        "metadata": [
            {
                "summary": "Mandatory alternate fields are missing",
                "fields": ["name or title"],
            }
        ]
    }
    assert actual_check is False
    assert error_detail == expected_error


def test_api_checks_check_metadata_ko2(swh_checks_deposit):
    """Missing mandatory fields should be caught

    """
    actual_check, error_detail = check_metadata(
        {
            "url": "something",
            "external_identifier": "something-else",
            "title": "foobar",
        }
    )

    expected_error = {
        "metadata": [{"summary": "Mandatory fields are missing", "fields": ["author"],}]
    }

    assert actual_check is False
    assert error_detail == expected_error
