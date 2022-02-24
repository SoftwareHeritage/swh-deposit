# Copyright (C) 2018-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import io

from swh.deposit.parsers import SWHXMLParser
from swh.deposit.utils import NAMESPACES


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

    assert (
        actual_result.findtext(
            "codemeta:license/codemeta:name",
            namespaces={"codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"},
        )
        == "GPL3.0"
    )
    assert (
        actual_result.findtext("codemeta:license/codemeta:name", namespaces=NAMESPACES)
        == "GPL3.0"
    )
    authors = actual_result.findall(
        "codemeta:author/codemeta:name", namespaces=NAMESPACES
    )
    assert len(authors) == 1
    assert authors[0].text == "author1"


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

    assert (
        actual_result.findtext(
            "codemeta:license/codemeta:name",
            namespaces={"codemeta": "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"},
        )
        == "GPL3.0"
    )
    assert (
        actual_result.findtext("codemeta:license/codemeta:name", namespaces=NAMESPACES)
        == "GPL3.0"
    )
    authors = actual_result.findall(
        "codemeta:author/codemeta:name", namespaces=NAMESPACES
    )
    assert len(authors) == 2
    assert authors[0].text == "author1"
    assert authors[1].text == "author2"
