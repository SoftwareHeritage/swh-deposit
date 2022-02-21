# Copyright (C) 2017-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict

import pytest

from swh.deposit.api.checks import (
    METADATA_PROVENANCE_KEY,
    SUGGESTED_FIELDS_MISSING,
    check_metadata,
)

METADATA_PROVENANCE_DICT: Dict[str, Any] = {
    "swh:deposit": {
        METADATA_PROVENANCE_KEY: {"schema:url": "some-metadata-provenance-url"}
    }
}


@pytest.mark.parametrize(
    "metadata_ok",
    [
        {
            "atom:url": "something",
            "atom:external_identifier": "something-else",
            "atom:name": "foo",
            "atom:author": "someone",
            **METADATA_PROVENANCE_DICT,
        },
        {
            "atom:url": "some url",
            "atom:external_identifier": "some id",
            "atom:title": "bar",
            "atom:author": "no one",
            **METADATA_PROVENANCE_DICT,
        },
        {
            "atom:url": "some url",
            "codemeta:name": "bar",
            "codemeta:author": "no one",
            **METADATA_PROVENANCE_DICT,
        },
        {
            "atom:url": "some url",
            "atom:external_identifier": "some id",
            "atom:title": "bar",
            "atom:author": "no one",
            "codemeta:datePublished": "2020-12-21",
            "codemeta:dateCreated": "2020-12-21",
        },
    ],
)
def test_api_checks_check_metadata_ok(metadata_ok, swh_checks_deposit):
    actual_check, detail = check_metadata(metadata_ok)
    assert actual_check is True, f"Unexpected result: {detail}"
    if "swh:deposit" in metadata_ok:
        # no missing suggested field
        assert detail is None
    else:
        # missing suggested field
        assert detail == {
            "metadata": [
                {
                    "fields": [METADATA_PROVENANCE_KEY],
                    "summary": SUGGESTED_FIELDS_MISSING,
                }
            ]
        }


@pytest.mark.parametrize(
    "metadata_ko,expected_summary",
    [
        (
            {
                "atom:url": "something",
                "atom:external_identifier": "something-else",
                "atom:author": "someone",
                **METADATA_PROVENANCE_DICT,
            },
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:name or atom:title or codemeta:name"],
            },
        ),
        (
            {
                "atom:url": "something",
                "atom:external_identifier": "something-else",
                "atom:title": "foobar",
                **METADATA_PROVENANCE_DICT,
            },
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:author or codemeta:author"],
            },
        ),
        (
            {
                "atom:url": "something",
                "atom:external_identifier": "something-else",
                "codemeta:title": "bar",
                "atom:author": "someone",
                **METADATA_PROVENANCE_DICT,
            },
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:name or atom:title or codemeta:name"],
            },
        ),
        (
            {
                "atom:url": "something",
                "atom:external_identifier": "something-else",
                "atom:title": "foobar",
                "author": "foo",
                **METADATA_PROVENANCE_DICT,
            },
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:author or codemeta:author"],
            },
        ),
        (
            {
                "atom:url": "something",
                "atom:external_identifier": "something-else",
                "atom:title": "foobar",
                "atom:authorblahblah": "foo",
                **METADATA_PROVENANCE_DICT,
            },
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:author or codemeta:author"],
            },
        ),
        (
            {
                "atom:url": "something",
                "atom:external_identifier": "something-else",
                "atom:author": "someone",
                **METADATA_PROVENANCE_DICT,
            },
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:name or atom:title or codemeta:name"],
            },
        ),
    ],
)
def test_api_checks_check_metadata_ko(
    metadata_ko, expected_summary, swh_checks_deposit
):
    actual_check, error_detail = check_metadata(metadata_ko)
    assert actual_check is False
    assert error_detail == {"metadata": [expected_summary]}


@pytest.mark.parametrize(
    "metadata_ko,expected_invalid_summary",
    [
        (
            {
                "atom:url": "some url",
                "atom:external_identifier": "some id",
                "atom:title": "bar",
                "atom:author": "no one",
                "codemeta:datePublished": "2020-aa-21",
                "codemeta:dateCreated": "2020-12-bb",
            },
            {
                "summary": "Invalid date format",
                "fields": ["codemeta:datePublished", "codemeta:dateCreated"],
            },
        ),
    ],
)
def test_api_checks_check_metadata_fields_ko_and_missing_suggested_fields(
    metadata_ko, expected_invalid_summary, swh_checks_deposit
):
    actual_check, error_detail = check_metadata(metadata_ko)
    assert actual_check is False
    assert error_detail == {
        "metadata": [expected_invalid_summary]
        + [{"fields": [METADATA_PROVENANCE_KEY], "summary": SUGGESTED_FIELDS_MISSING,}]
    }
