# Copyright (C) 2018-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import OrderedDict
import io

import pytest

from swh.deposit.parsers import SWHXMLParser, parse_swh_reference, parse_xml
from swh.model.exceptions import ValidationError
from swh.model.identifiers import parse_swhid


def test_parsing_without_duplicates():
    xml_no_duplicate = io.BytesIO(
        b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
    <title>Awesome Compiler</title>
    <codemeta:license>
        <codemeta:name>GPL3.0</codemeta:name>
        <codemeta:url>https://opensource.org/licenses/GPL-3.0</codemeta:url>
    </codemeta:license>
    <codemeta:runtimePlatform>Python3</codemeta:runtimePlatform>
    <codemeta:author>
        <codemeta:name>author1</codemeta:name>
        <codemeta:affiliation>Inria</codemeta:affiliation>
    </codemeta:author>
    <codemeta:programmingLanguage>ocaml</codemeta:programmingLanguage>
    <codemeta:issueTracker>http://issuetracker.com</codemeta:issueTracker>
</entry>"""
    )

    actual_result = SWHXMLParser().parse(xml_no_duplicate)
    expected_dict = OrderedDict(
        [
            ("title", "Awesome Compiler"),
            (
                "codemeta:license",
                OrderedDict(
                    [
                        ("codemeta:name", "GPL3.0"),
                        ("codemeta:url", "https://opensource.org/licenses/GPL-3.0"),
                    ]
                ),
            ),
            ("codemeta:runtimePlatform", "Python3"),
            (
                "codemeta:author",
                OrderedDict(
                    [("codemeta:name", "author1"), ("codemeta:affiliation", "Inria")]
                ),
            ),
            ("codemeta:programmingLanguage", "ocaml"),
            ("codemeta:issueTracker", "http://issuetracker.com"),
        ]
    )
    assert expected_dict == actual_result


def test_parsing_with_duplicates():
    xml_with_duplicates = io.BytesIO(
        b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom"
       xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
    <title>Another Compiler</title>
    <codemeta:runtimePlatform>GNU/Linux</codemeta:runtimePlatform>
    <codemeta:license>
        <codemeta:name>GPL3.0</codemeta:name>
        <codemeta:url>https://opensource.org/licenses/GPL-3.0</codemeta:url>
    </codemeta:license>
    <codemeta:runtimePlatform>Un*x</codemeta:runtimePlatform>
    <codemeta:author>
        <codemeta:name>author1</codemeta:name>
        <codemeta:affiliation>Inria</codemeta:affiliation>
    </codemeta:author>
    <codemeta:author>
        <codemeta:name>author2</codemeta:name>
        <codemeta:affiliation>Inria</codemeta:affiliation>
    </codemeta:author>
    <codemeta:programmingLanguage>ocaml</codemeta:programmingLanguage>
    <codemeta:programmingLanguage>haskell</codemeta:programmingLanguage>
    <codemeta:license>
        <codemeta:name>spdx</codemeta:name>
        <codemeta:url>http://spdx.org</codemeta:url>
    </codemeta:license>
    <codemeta:programmingLanguage>python3</codemeta:programmingLanguage>
</entry>"""
    )

    actual_result = SWHXMLParser().parse(xml_with_duplicates)

    expected_dict = OrderedDict(
        [
            ("title", "Another Compiler"),
            ("codemeta:runtimePlatform", ["GNU/Linux", "Un*x"]),
            (
                "codemeta:license",
                [
                    OrderedDict(
                        [
                            ("codemeta:name", "GPL3.0"),
                            ("codemeta:url", "https://opensource.org/licenses/GPL-3.0"),
                        ]
                    ),
                    OrderedDict(
                        [("codemeta:name", "spdx"), ("codemeta:url", "http://spdx.org")]
                    ),
                ],
            ),
            (
                "codemeta:author",
                [
                    OrderedDict(
                        [
                            ("codemeta:name", "author1"),
                            ("codemeta:affiliation", "Inria"),
                        ]
                    ),
                    OrderedDict(
                        [
                            ("codemeta:name", "author2"),
                            ("codemeta:affiliation", "Inria"),
                        ]
                    ),
                ],
            ),
            ("codemeta:programmingLanguage", ["ocaml", "haskell", "python3"]),
        ]
    )
    assert expected_dict == actual_result


@pytest.fixture
def xml_with_origin_reference():
    xml_data = """<?xml version="1.0"?>
  <entry xmlns="http://www.w3.org/2005/Atom"
           xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
           xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">
      <swh:deposit>
        <swh:reference>
          <swh:origin url="{url}"/>
        </swh:reference>
      </swh:deposit>
  </entry>
    """
    return xml_data.strip()


def test_parse_swh_reference_origin(xml_with_origin_reference):
    url = "https://url"
    xml_data = xml_with_origin_reference.format(url=url)
    metadata = parse_xml(xml_data)

    actual_origin = parse_swh_reference(metadata)
    assert actual_origin == url


@pytest.fixture
def xml_with_empty_reference():
    xml_data = """<?xml version="1.0"?>
  <entry xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">
      <swh:deposit>
        {swh_reference}
      </swh:deposit>
  </entry>
    """
    return xml_data.strip()


@pytest.mark.parametrize(
    "xml_ref",
    [
        "",
        "<swh:reference></swh:reference>",
        "<swh:reference><swh:object /></swh:reference>",
        """<swh:reference><swh:object swhid="" /></swh:reference>""",
    ],
)
def test_parse_swh_reference_empty(xml_with_empty_reference, xml_ref):
    xml_body = xml_with_empty_reference.format(swh_reference=xml_ref)
    metadata = parse_xml(xml_body)

    assert parse_swh_reference(metadata) is None


@pytest.fixture
def xml_with_swhid(atom_dataset):
    return atom_dataset["entry-data-with-swhid"]


@pytest.mark.parametrize(
    "swhid",
    [
        "swh:1:cnt:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=https://hal.archives-ouvertes.fr/hal-01243573;visit=swh:1:snp:4fc1e36fca86b2070204bedd51106014a614f321;anchor=swh:1:rev:9c5de20cfb54682370a398fcc733e829903c8cba;path=/moranegg-AffectationRO-df7f68b/",  # noqa
        "swh:1:dir:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;anchor=swh:1:dir:9c5de20cfb54682370a398fcc733e829903c8cba",  # noqa
        "swh:1:rev:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;anchor=swh:1:rev:9c5de20cfb54682370a398fcc733e829903c8cba",  # noqa
        "swh:1:rel:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;anchor=swh:1:rel:9c5de20cfb54682370a398fcc733e829903c8cba",  # noqa
        "swh:1:snp:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;anchor=swh:1:snp:9c5de20cfb54682370a398fcc733e829903c8cba",  # noqa
        "swh:1:dir:31b5c8cc985d190b5a7ef4878128ebfdc2358f49",
    ],
)
def test_parse_swh_reference_swhid(swhid, xml_with_swhid):
    xml_data = xml_with_swhid.format(swhid=swhid)
    metadata = parse_xml(xml_data)

    actual_swhid = parse_swh_reference(metadata)
    assert actual_swhid is not None

    expected_swhid = parse_swhid(swhid)
    assert actual_swhid == expected_swhid


@pytest.mark.parametrize(
    "invalid_swhid,error_msg",
    [
        ("swh:1:cnt:31b5c8cc985d190b5a7ef4878128ebfdc235", "Unexpected length"),
        (
            "swh:1:dir:c4993c872593e960dc84e4430dbbfbc34fd706d0;visit=swh:1:rev:0175049fc45055a3824a1675ac06e3711619a55a",  # noqa
            "visit qualifier should be a core SWHID with type",
        ),
        (
            "swh:1:rev:c4993c872593e960dc84e4430dbbfbc34fd706d0;anchor=swh:1:cnt:b5f505b005435fa5c4fa4c279792bd7b17167c04;path=/",  # noqa
            "anchor qualifier should be a core SWHID with type one of",
        ),
        (
            "swh:1:rev:c4993c872593e960dc84e4430dbbfbc34fd706d0;visit=swh:1:snp:0175049fc45055a3824a1675ac06e3711619a55a;anchor=swh:1:snp:b5f505b005435fa5c4fa4c279792bd7b17167c04",  # noqa
            "anchor=swh:1:snp",
        ),
    ],
)
def test_parse_swh_reference_invalid_swhid(invalid_swhid, error_msg, xml_with_swhid):
    """Unparsable swhid should raise

    """
    xml_invalid_swhid = xml_with_swhid.format(swhid=invalid_swhid)
    metadata = parse_xml(xml_invalid_swhid)

    with pytest.raises(ValidationError, match=error_msg):
        parse_swh_reference(metadata)
