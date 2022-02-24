# Copyright (C) 2017-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# disable flake8 on this file because of line length
# flake8: noqa

import re
import textwrap
from typing import Any, Dict
from xml.etree import ElementTree

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

XMLNS = """xmlns="http://www.w3.org/2005/Atom"
                   xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit"
                   xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
                   xmlns:schema="http://schema.org/" """

PROVENANCE_XML = """
                <swh:deposit>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
                </swh:deposit>"""

_parameters1 = [
    textwrap.dedent(metadata_ok)
    for (metadata_ok,) in [
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <name>foo</name>
                <author>someone</author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <name>foo</name>
                <author>no one</author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>some url</url>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>no one</codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>some url</url>
                <external_identifier>some id</external_identifier>
                <name>nar</name>
                <author>no one</author>
                <codemeta:datePublished>2020-12-21</codemeta:datePublished>
                <codemeta:dateCreated>2020-12-21</codemeta:dateCreated>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
            </entry>
            """,
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:add_to_origin>
                        <swh:origin url="http://example.org" />
                    </swh:add_to_origin>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
                </swh:deposit>
            </entry>
            """,
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:reference>
                        <swh:origin url="http://example.org" />
                    </swh:reference>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
                </swh:deposit>
            </entry>
            """,
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:reference>
                        <swh:object swhid="swh:1:dir:0000000000000000000000000000000000000000" />
                    </swh:reference>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
                </swh:deposit>
            </entry>
            """,
        ),
    ]
]


@pytest.mark.parametrize(
    "metadata_ok", _parameters1,
)
def test_api_checks_check_metadata_ok(metadata_ok, swh_checks_deposit):
    actual_check, detail = check_metadata(ElementTree.fromstring(metadata_ok))
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


_parameters2 = [
    (textwrap.dedent(metadata_ko), expected_summary)
    for (metadata_ko, expected_summary) in [
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <author>someone</author>
                {PROVENANCE_XML}
            </entry>
            """,
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:name or atom:title or codemeta:name"],
            },
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>foobar</title>
                {PROVENANCE_XML}
            </entry>
            """,
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:author or codemeta:author"],
            },
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <codemeta:title>bar</codemeta:title>
                <author>someone</author>
                {PROVENANCE_XML}
            </entry>
            """,
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:name or atom:title or codemeta:name"],
            },
        ),
        (
            f"""\
            <entry xmlns:atom="http://www.w3.org/2005/Atom"
                   xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit"
                   xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
                   xmlns:schema="http://schema.org/">
                <atom:url>something</atom:url>
                <atom:external_identifier>something-else</atom:external_identifier>
                <atom:title>foobar</atom:title>
                <author>foo</author>
                {PROVENANCE_XML}
            </entry>
            """,
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:author or codemeta:author"],
            },
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <authorblahblah>someone</authorblahblah>
                {PROVENANCE_XML}
            </entry>
            """,
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:author or codemeta:author"],
            },
        ),
    ]
]


@pytest.mark.parametrize("metadata_ko,expected_summary", _parameters2)
def test_api_checks_check_metadata_ko(
    metadata_ko, expected_summary, swh_checks_deposit
):
    actual_check, error_detail = check_metadata(ElementTree.fromstring(metadata_ko))
    assert actual_check is False
    assert error_detail == {"metadata": [expected_summary]}


_parameters3 = [
    (textwrap.dedent(metadata_ko), expected_summary)
    for (metadata_ko, expected_summary) in [
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <codemeta:datePublished>2020-aa-21</codemeta:datePublished>
                <codemeta:dateCreated>2020-12-bb</codemeta:dateCreated>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: invalid value '2020-aa-21'.*",
                    "fields": ["codemeta:datePublished"],
                },
                {
                    "summary": ".*Reason: invalid value '2020-12-bb'.*",
                    "fields": ["codemeta:dateCreated"],
                },
            ],
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>some url</url>
                <external_identifier>someid</external_identifier>
                <title>bar</title>
                <author>no one</author>
                <codemeta:datePublished>2020-aa-21</codemeta:datePublished>
                <codemeta:dateCreated>2020-12-bb</codemeta:dateCreated>
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: invalid value '2020-aa-21'.*",
                    "fields": ["codemeta:datePublished"],
                },
                {
                    "summary": ".*Reason: invalid value '2020-12-bb'.*",
                    "fields": ["codemeta:dateCreated"],
                },
            ],
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:invalid>
                        <swh:origin url="http://example.org" />
                    </swh:invalid>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": (
                        r".*Reason: Unexpected child with tag 'swh:invalid'.*"
                        r"Instance:.*swh:invalid.*"
                    ),
                    "fields": ["swh:deposit"],
                }
            ],
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:add_to_origin>
                        <swh:origin url="http://example.org" />
                    </swh:add_to_origin>
                    <swh:add_to_origin>
                        <swh:origin url="http://example.org" />
                    </swh:add_to_origin>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": (
                        r".*Reason: Unexpected child with tag 'swh:add_to_origin'.*"
                    ),
                    "fields": ["swh:deposit"],
                }
            ],
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:add_to_origin>
                        <swh:origin url="http://example.org" />
                    </swh:add_to_origin>
                    <swh:create_origin>
                        <swh:origin url="http://example.org" />
                    </swh:create_origin>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": (
                        r".*Reason: assertion test if false.*"
                        r"Schema:\n*"
                        r' *<xsd:assert[^>]+ id="swhdeposit-incompatible-create-and-add".*'
                    ),
                    "fields": ["swh:deposit"],
                }
            ],
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:create_origin>
                        <swh:origin url="http://example.org" />
                    </swh:create_origin>
                    <swh:reference>
                        <swh:origin url="http://example.org" />
                    </swh:reference>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": (
                        r".*Reason: assertion test if false.*"
                        r"Schema:\n*"
                        r' *<xsd:assert[^>]+ id="swhdeposit-incompatible-create-and-reference".*'
                    ),
                    "fields": ["swh:deposit"],
                }
            ],
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:add_to_origin>
                        <swh:origin url="http://example.org" />
                    </swh:add_to_origin>
                    <swh:reference>
                        <swh:origin url="http://example.org" />
                    </swh:reference>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": (
                        r".*Reason: assertion test if false.*"
                        r"Schema:\n*"
                        r' *<xsd:assert[^>]+ id="swhdeposit-incompatible-add-and-reference".*'
                    ),
                    "fields": ["swh:deposit"],
                }
            ],
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:reference>
                        <swh:object swhid="swh:1:dir:0000000000000000000000000000000000000000" />
                        <swh:origin url="http://example.org" />
                    </swh:reference>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": r".*Reason: Unexpected child with tag 'swh:origin'.*",
                    "fields": ["swh:deposit"],
                },
            ],
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:reference>
                        <swh:origin url="http://example.org" />
                        <swh:origin url="http://example.org" />
                    </swh:reference>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": r".*Reason: Unexpected child with tag 'swh:origin'.*",
                    "fields": ["swh:deposit"],
                },
            ],
        ),
        (
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <external_identifier>something-else</external_identifier>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:reference>
                        <swh:origin url="http://example.org" />
                        <swh:object swhid="swh:1:dir:0000000000000000000000000000000000000000" />
                    </swh:reference>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": r".*Reason: Unexpected child with tag 'swh:object'.*",
                    "fields": ["swh:deposit"],
                },
            ],
        ),
    ]
]


@pytest.mark.parametrize("metadata_ko,expected_summaries", _parameters3)
def test_api_checks_check_metadata_ko_schema(
    metadata_ko, expected_summaries, swh_checks_deposit
):
    actual_check, error_detail = check_metadata(ElementTree.fromstring(metadata_ko))
    assert actual_check is False
    assert len(error_detail["metadata"]) == len(expected_summaries), error_detail[
        "metadata"
    ]

    for (detail, expected_summary) in zip(error_detail["metadata"], expected_summaries):
        assert detail["fields"] == expected_summary["fields"]

        # xmlschema returns very detailed errors, we cannot reasonably test them
        # for equality
        summary = detail["summary"]
        assert re.match(
            expected_summary["summary"], summary, re.DOTALL
        ), f"Failed to match {expected_summary['summary']!r} with:\n{summary}"
