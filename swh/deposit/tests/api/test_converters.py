# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.deposit.api.converters import convert_status_detail


def test_convert_status_detail_empty():
    for status_detail in [{}, {"dummy-keys": []}, None]:
        assert convert_status_detail(status_detail) is None


def test_convert_status_detail():
    status_detail = {
        "url": {
            "summary": "At least one url field must be compatible with the client's domain name. The following url fields failed the check",  # noqa
            "fields": ["blahurl", "testurl"],
        },
        "metadata": [
            {"summary": "Mandatory fields missing", "fields": ["url", "title"],},
            {
                "summary": "Alternate fields missing",
                "fields": ["name or title", "url or badurl"],
            },
        ],
        "archive": [{"summary": "Unreadable archive", "fields": ["1"],}],
    }

    expected_status_detail = """- Mandatory fields missing (url, title)
- Alternate fields missing (name or title, url or badurl)
- Unreadable archive (1)
- At least one url field must be compatible with the client's domain name. The following url fields failed the check (blahurl, testurl)
"""  # noqa

    actual_status_detail = convert_status_detail(status_detail)
    assert actual_status_detail == expected_status_detail


def test_convert_status_detail_2():
    status_detail = {
        "url": {
            "summary": "At least one compatible url field. Failed",
            "fields": ["testurl"],
        },
        "metadata": [{"summary": "Mandatory fields missing", "fields": ["name"],},],
        "archive": [
            {"summary": "Invalid archive", "fields": ["2"],},
            {"summary": "Unsupported archive", "fields": ["1"],},
        ],
    }

    expected_status_detail = """- Mandatory fields missing (name)
- Invalid archive (2)
- Unsupported archive (1)
- At least one compatible url field. Failed (testurl)
"""

    actual_status_detail = convert_status_detail(status_detail)
    assert actual_status_detail == expected_status_detail


def test_convert_status_detail_3():
    status_detail = {
        "url": {"summary": "At least one compatible url field",},
    }

    expected_status_detail = "- At least one compatible url field\n"
    actual_status_detail = convert_status_detail(status_detail)
    assert actual_status_detail == expected_status_detail


def test_convert_status_detail_edge_case():
    status_detail = {
        "url": {
            "summary": "At least one compatible url field. Failed",
            "fields": ["testurl"],
        },
        "metadata": [
            {"summary": "Mandatory fields missing", "fields": ["9", 10, 1.212],},
        ],
        "archive": [
            {"summary": "Invalid archive", "fields": ["3"],},
            {"summary": "Unsupported archive", "fields": [2],},
        ],
    }

    expected_status_detail = """- Mandatory fields missing (9, 10, 1.212)
- Invalid archive (3)
- Unsupported archive (2)
- At least one compatible url field. Failed (testurl)
"""

    actual_status_detail = convert_status_detail(status_detail)
    assert actual_status_detail == expected_status_detail
