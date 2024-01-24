# Copyright (C) 2017-2024  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# disable flake8 on this file because of line length
# flake8: noqa

import pprint
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
    pytest.param(textwrap.dedent(metadata_ok), id=id_)
    for (
        id_,
        metadata_ok,
    ) in [
        (
            "atom-only-with-name",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <name>foo</name>
                <author>someone</author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "atom-only-with-title",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <title>bar</title>
                <author>someone</author>
            </entry>
            """,
        ),
        (
            "atom-only-and-id",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <name>foo</name>
                <author>no one</author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "atom-and-codemeta-minimal",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>no one</codemeta:name>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "unknown-schema-inner-element-after",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <schema:unknown-tag>should allow anything here</schema:unknown-tag>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "unknown-schema-inner-element-before",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <schema:unknown-tag>should allow anything here</schema:unknown-tag>
                    <codemeta:name>someone</codemeta:name>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "unknown-schema-inner-element-before-and-after",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <schema:unknown-tag>should allow anything here</schema:unknown-tag>
                    <codemeta:name>someone</codemeta:name>
                    <schema:unknown-tag>should allow anything here</schema:unknown-tag>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "identifier-is-halid",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>The Author</codemeta:name>
                </codemeta:author>
                <codemeta:identifier>hal-12345</codemeta:identifier>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "identifier-is-propertyvalue",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>The Author</codemeta:name>
                </codemeta:author>
                <schema:identifier>
                    <codemeta:type>schema:PropertyValue</codemeta:type>
                    <schema:propertyID>HAL-ID</schema:propertyID>
                    <schema:value>hal-02527911</schema:value>
                </schema:identifier>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "codemeta-dates",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <id>some id</id>
                <name>nar</name>
                <author>no one</author>
                <codemeta:datePublished>2020-12-21</codemeta:datePublished>
                <codemeta:dateCreated>2020-12-21</codemeta:dateCreated>
                <codemeta:dateModified>2020-12-25</codemeta:dateModified>
                <codemeta:embargoDate>2020-12-25</codemeta:embargoDate>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "codemeta-date-month",
            # Allowed by ISO8601, therefore by schema:Date, but not by xsd:date
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <id>some id</id>
                <name>nar</name>
                <author>no one</author>
                <codemeta:datePublished>2020-12</codemeta:datePublished>
                <codemeta:dateCreated>2020-12</codemeta:dateCreated>
                <codemeta:dateModified>2020-12</codemeta:dateModified>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "codemeta-date-year",
            # Allowed by ISO8601, therefore by schema:Date, but not by xsd:date
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <id>some id</id>
                <name>nar</name>
                <author>no one</author>
                <codemeta:datePublished>2020</codemeta:datePublished>
                <codemeta:dateCreated>2020</codemeta:dateCreated>
                <codemeta:dateModified>2020</codemeta:dateModified>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "codemeta-datetimes",
            # technically, only Date is allowed for datePublished; but we allow DateTime
            # for backward compatibility with old swh-deposit versions
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <id>some id</id>
                <name>nar</name>
                <author>no one</author>
                <codemeta:datePublished>2020-12-21T12:00:00</codemeta:datePublished>
                <codemeta:dateCreated>2020-12-21T12:00:00</codemeta:dateCreated>
                <codemeta:dateModified>2020-12-25T12:00:00</codemeta:dateModified>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "author-two-names",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <codemeta:name>an alias</codemeta:name>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            # Required by codemeta.jsonld, but forbidden by
            # https://codemeta.github.io/terms/
            "element-in--affiliation",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <codemeta:affiliation>
                        <codemeta:name>My Orga</codemeta:name>
                    </codemeta:affiliation>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            # Forbidden by codemeta.jsonld, but required by
            # https://codemeta.github.io/terms/
            "chardata-in-affiliation",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <codemeta:affiliation>My Orga</codemeta:affiliation>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
        (
            "swh:add_to_origin",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
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
            "swh:reference-origin",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
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
            "swh:reference-object",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
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
        (
            # a full example with every tag we know
            "codemeta-full",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <name>foo</name>
                <author>someone</author>
                <codemeta:author>
                    <codemeta:name>The Author</codemeta:name>
                    <codemeta:id>http://example.org/~theauthor/</codemeta:id>
                    <codemeta:email>author@example.org</codemeta:email>
                    <codemeta:affiliation>
                        <codemeta:name>University 1</codemeta:name>
                    </codemeta:affiliation>
                    <codemeta:identifier>https://sandbox.orcid.org/0000-0002-9227-8514</codemeta:identifier>
                </codemeta:author>
                <codemeta:contributor>
                    <codemeta:name>A Contributor</codemeta:name>
                    <codemeta:affiliation>
                        <codemeta:name>University 2</codemeta:name>
                    </codemeta:affiliation>
                </codemeta:contributor>
                <codemeta:maintainer>
                    <codemeta:name>A Maintainer</codemeta:name>
                    <codemeta:affiliation>
                        <codemeta:name>University 3</codemeta:name>
                    </codemeta:affiliation>
                </codemeta:maintainer>
                <codemeta:copyrightHolder>
                    <codemeta:name>University 3</codemeta:name>
                </codemeta:copyrightHolder>
                <codemeta:creator>
                    <codemeta:name>A Maintainer</codemeta:name>
                </codemeta:creator>
                <codemeta:applicationCategory>something</codemeta:applicationCategory>
                <codemeta:applicationSubCategory>something else</codemeta:applicationSubCategory>
                <codemeta:installUrl>http://example.org/</codemeta:installUrl>
                <codemeta:releaseNotes>Blah blah</codemeta:releaseNotes>
                <codemeta:softwareVersion>1.0.0</codemeta:softwareVersion>
                <codemeta:version>1.0.0</codemeta:version>
                <codemeta:keywords>kw1</codemeta:keywords>
                <codemeta:keywords>kw2</codemeta:keywords>
                <codemeta:description>Blah blah</codemeta:description>
                <codemeta:url>http://example.org/</codemeta:url>
                <codemeta:issueTracker>http://example.org/</codemeta:issueTracker>
                <codemeta:readme>http://example.org/</codemeta:readme>
                {PROVENANCE_XML}
            </entry>
            """,
        ),
    ]
]


@pytest.mark.parametrize(
    "metadata_ok",
    _parameters1,
)
def test_api_checks_check_metadata_ok(metadata_ok, swh_checks_deposit):
    actual_check, detail = check_metadata(ElementTree.fromstring(metadata_ok))
    assert actual_check is True, f"Unexpected result:\n{pprint.pformat(detail)}"
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
    pytest.param(textwrap.dedent(metadata_ko), expected_summary, id=id_)
    for (id_, metadata_ko, expected_summary) in [
        (
            "no-name-or-title",
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <id>something-else</id>
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
            "no-author",
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <id>something-else</id>
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
            "wrong-root-element",
            f"""\
            <not-entry {XMLNS}>
                <url>some url</url>
                <title>bar</title>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <codemeta:name>an alias</codemeta:name>
                </codemeta:author>
                {PROVENANCE_XML}
            </not-entry>
            """,
            {
                "fields": ["atom:entry"],
                "summary": "Root element should be "
                "{http://www.w3.org/2005/Atom}entry, but it is "
                "{http://www.w3.org/2005/Atom}not-entry",
            },
        ),
        (
            "wrong-root-element-namespace",
            f"""\
            <codemeta:entry {XMLNS}>
                <url>some url</url>
                <title>bar</title>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <codemeta:name>an alias</codemeta:name>
                </codemeta:author>
            </codemeta:entry>
            """,
            {
                "fields": ["atom:entry"],
                "summary": "Root element should be "
                "{http://www.w3.org/2005/Atom}entry, but it is "
                "{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}entry",
            },
        ),
        (
            "wrong-root-element-no-namespace",
            f"""\
            <entry xmlns:atom="http://www.w3.org/2005/Atom"
                   xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit"
                   xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
                   xmlns:schema="http://schema.org/">
                <atom:url>some url</atom:url>
                <codemeta:name>bar</codemeta:name>
                <title>bar</title>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <codemeta:name>an alias</codemeta:name>
                </codemeta:author>
            </entry>
            """,
            {
                "fields": ["atom:entry"],
                "summary": "Root element should be "
                "{http://www.w3.org/2005/Atom}entry, but it is entry",
            },
        ),
        (
            "wrong-root-element-default-namespace",
            f"""\
            <entry xmlns:atom="http://www.w3.org/2005/Atom"
                   xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit"
                   xmlns="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
                   xmlns:schema="http://schema.org/">
                <atom:url>some url</atom:url>
                <name>bar</name>
                <author>
                    <name>someone</name>
                    <name>an alias</name>
                </author>
            </entry>
            """,
            {
                "fields": ["atom:entry"],
                "summary": "Root element should be "
                "{http://www.w3.org/2005/Atom}entry, but it is "
                "{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}entry",
            },
        ),
        (
            "wrong-title-namespace",
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <id>something-else</id>
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
            "wrong-author-namespace",
            f"""\
            <atom:entry xmlns:atom="http://www.w3.org/2005/Atom"
                        xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit"
                        xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
                        xmlns:schema="http://schema.org/">
                <atom:url>something</atom:url>
                <atom:id>something-else</atom:id>
                <atom:title>foobar</atom:title>
                <author>foo</author>
                {PROVENANCE_XML}
            </atom:entry>
            """,
            {
                "summary": "Mandatory fields are missing",
                "fields": ["atom:author or codemeta:author"],
            },
        ),
        (
            "wrong-author-tag",
            f"""\
            <entry {XMLNS}>
                <url>something</url>
                <id>something-else</id>
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
        (
            "unknown-atom",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <unknown-tag>but in known namespace</unknown-tag>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            {
                "summary": "unknown-tag is not a valid Atom element, see "
                "https://datatracker.ietf.org/doc/html/rfc4287",
                "fields": ["unknown-tag"],
            },
        ),
        (
            "unknown-codemeta",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:unknown-tag>but in known namespace</codemeta:unknown-tag>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            {
                "summary": "unknown-tag is not a valid Codemeta 2.0 term, see "
                "https://github.com/codemeta/codemeta/blob/2.0/codemeta.jsonld",
                "fields": ["unknown-tag"],
            },
        ),
        (
            "unknown-atom-in-codemeta",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <unknown-tag>but in known namespace</unknown-tag>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            {
                "summary": "unknown-tag is not a valid Atom element, see "
                "https://datatracker.ietf.org/doc/html/rfc4287",
                "fields": ["unknown-tag"],
            },
        ),
        (
            "unknown-codemeta-in-codemeta",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <codemeta:unknown-tag>but in known namespace</codemeta:unknown-tag>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            {
                "summary": "unknown-tag is not a valid Codemeta 2.0 term, see "
                "https://github.com/codemeta/codemeta/blob/2.0/codemeta.jsonld",
                "fields": ["unknown-tag"],
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
    pytest.param(textwrap.dedent(metadata_ko), expected_summary, id=id_)
    for (id_, metadata_ko, expected_summary) in [
        (
            "child-element-in-name",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>
                    <codemeta:name>bar</codemeta:name>
                </codemeta:name>
                <author>no one</author>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: a simple content element can't have child elements.*",
                    "fields": ["codemeta:name"],
                },
            ],
        ),
        (
            "affiliation-with-no-name",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <codemeta:affiliation>
                        <codemeta:url>http://example.org</codemeta:url>
                    </codemeta:affiliation>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: affiliation does not have a <codemeta:name> element.*",
                    "fields": ["codemeta:author"],
                },
            ],
        ),
        (
            "empty-affiliation",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>someone</codemeta:name>
                    <codemeta:affiliation>
                    </codemeta:affiliation>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: affiliation does not have a <codemeta:name> element.*",
                    "fields": ["codemeta:author"],
                },
            ],
        ),
        (
            "chardata-in-author",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>no one</codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: character data between child elements.*",
                    "fields": ["codemeta:author"],
                },
            ],
        ),
        (
            "author-with-no-name",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <schema:unknown-tag>should allow anything here</schema:unknown-tag>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Tag '?codemeta:name'? expected.*",
                    "fields": ["codemeta:author"],
                },
            ],
        ),
        (
            "contributor-with-no-name",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>should allow anything here</codemeta:name>
                </codemeta:author>
                <codemeta:contributor>
                    <schema:unknown-tag>abc</schema:unknown-tag>
                </codemeta:contributor>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Tag '?codemeta:name'? expected.*",
                    "fields": ["codemeta:contributor"],
                },
            ],
        ),
        (
            "maintainer-with-no-name",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>should allow anything here</codemeta:name>
                </codemeta:author>
                <codemeta:maintainer>
                    <schema:unknown-tag>abc</schema:unknown-tag>
                </codemeta:maintainer>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Tag '?codemeta:name'? expected.*",
                    "fields": ["codemeta:maintainer"],
                },
            ],
        ),
        (
            "id-is-not-url",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>The Author</codemeta:name>
                    <codemeta:id>http://not a url/</codemeta:id>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: 'http://not a url/' is not a valid URI.*",
                    "fields": ["codemeta:author"],
                },
            ],
        ),
        (
            "identifier-is-invalid-url",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>The Author</codemeta:name>
                    <codemeta:identifier>http://[invalid-url/</codemeta:identifier>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": (
                        r".*Reason: 'http://\[invalid-url/' is not a valid URI.*"
                    ),
                    "fields": ["codemeta:author"],
                },
            ],
        ),
        (
            "identifier-is-not-url",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>The Author</codemeta:name>
                    <codemeta:identifier>http://not a url/</codemeta:identifier>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: 'http://not a url/' is not a valid URI.*",
                    "fields": ["codemeta:author"],
                },
            ],
        ),
        (
            "identifier-is-not-url2",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>
                    <codemeta:name>The Author</codemeta:name>
                    <codemeta:identifier>not a url</codemeta:identifier>
                </codemeta:author>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: 'not a url' is not an absolute URI.*",
                    "fields": ["codemeta:author"],
                },
            ],
        ),
        (
            "invalid-dates",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
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
            "invalid-dateModified",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <id>someid</id>
                <title>bar</title>
                <author>no one</author>
                <codemeta:dateModified>2020-12-aa</codemeta:dateModified>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: invalid value '2020-12-aa'.*",
                    "fields": ["codemeta:dateModified"],
                },
            ],
        ),
        (
            "invalid-embargoDate",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <id>someid</id>
                <title>bar</title>
                <author>no one</author>
                <codemeta:embargoDate>2022-02-28T12:00:00</codemeta:embargoDate>
                {PROVENANCE_XML}
            </entry>
            """,
            [
                {
                    "summary": ".*Invalid datetime string '2022-02-28T12:00:00'.*",
                    "fields": ["codemeta:embargoDate"],
                },
            ],
        ),
        (
            "error-and-missing-provenance",
            f"""\
            <entry {XMLNS}>
                <uri>some url</uri>
                <codemeta:name>bar</codemeta:name>
                <codemeta:author>no one</codemeta:author>
            </entry>
            """,
            [
                {
                    "summary": ".*Reason: character data between child elements.*",
                    "fields": ["codemeta:author"],
                },
                {
                    "summary": "Suggested fields are missing",
                    "fields": ["swh:metadata-provenance"],
                },
            ],
        ),
        (
            "unknown-tag-in-swh-namespace",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:invalid>
                        <swh:origin url="http://example.org" />
                    </swh:invalid>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
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
            "multiple-swh:add_to_origin",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:add_to_origin>
                        <swh:origin url="http://example.org" />
                    </swh:add_to_origin>
                    <swh:add_to_origin>
                        <swh:origin url="http://example.org" />
                    </swh:add_to_origin>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
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
            "swh:add_to_origin-and-swh:create_origin",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:add_to_origin>
                        <swh:origin url="http://example.org" />
                    </swh:add_to_origin>
                    <swh:create_origin>
                        <swh:origin url="http://example.org" />
                    </swh:create_origin>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": (
                        r".*Reason: assertion test if false.*"
                        r"Schema.*:\n*"
                        r' *<xsd:assert[^>]+ id="swhdeposit-incompatible-create-and-add".*'
                    ),
                    "fields": ["swh:deposit"],
                }
            ],
        ),
        (
            "swh:reference-and-swh:create_origin",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:create_origin>
                        <swh:origin url="http://example.org" />
                    </swh:create_origin>
                    <swh:reference>
                        <swh:origin url="http://example.org" />
                    </swh:reference>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": (
                        r".*Reason: assertion test if false.*"
                        r"Schema.*:\n*"
                        r' *<xsd:assert[^>]+ id="swhdeposit-incompatible-create-and-reference".*'
                    ),
                    "fields": ["swh:deposit"],
                }
            ],
        ),
        (
            "swh:add_to_origin-and-swh:reference",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:add_to_origin>
                        <swh:origin url="http://example.org" />
                    </swh:add_to_origin>
                    <swh:reference>
                        <swh:origin url="http://example.org" />
                    </swh:reference>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
                </swh:deposit>
            </entry>
            """,
            [
                {
                    "summary": (
                        r".*Reason: assertion test if false.*"
                        r"Schema.*:\n*"
                        r' *<xsd:assert[^>]+ id="swhdeposit-incompatible-add-and-reference".*'
                    ),
                    "fields": ["swh:deposit"],
                }
            ],
        ),
        (
            "swh:reference-two-children",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:reference>
                        <swh:object swhid="swh:1:dir:0000000000000000000000000000000000000000" />
                        <swh:origin url="http://example.org" />
                    </swh:reference>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
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
            "swh:reference-two-origins",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:reference>
                        <swh:origin url="http://example.org" />
                        <swh:origin url="http://example.org" />
                    </swh:reference>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
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
            "swh:reference-two-objects",
            f"""\
            <entry {XMLNS}>
                <uri>something</uri>
                <id>something-else</id>
                <title>bar</title>
                <author>someone</author>
                <swh:deposit>
                    <swh:reference>
                        <swh:object swhid="swh:1:dir:1111111111111111111111111111111111111111" />
                        <swh:object swhid="swh:1:dir:0000000000000000000000000000000000000000" />
                    </swh:reference>
                    <swh:metadata-provenance>
                        <schema:url>some-metadata-provenance-url</schema:url>
                    </swh:metadata-provenance>
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

    for detail, expected_summary in zip(error_detail["metadata"], expected_summaries):
        assert detail["fields"] == expected_summary["fields"]

        # xmlschema returns very detailed errors, we cannot reasonably test them
        # for equality
        summary = detail["summary"]
        assert re.match(
            expected_summary["summary"], summary, re.DOTALL
        ), f"Failed to match {expected_summary['summary']!r} with:\n{summary}"
