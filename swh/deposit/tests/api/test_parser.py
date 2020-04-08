# Copyright (C) 2018-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import io

from collections import OrderedDict

from swh.deposit.parsers import SWHXMLParser


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
            ("@xmlns", "http://www.w3.org/2005/Atom"),
            ("@xmlns:codemeta", "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"),
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
            ("@xmlns", "http://www.w3.org/2005/Atom"),
            ("@xmlns:codemeta", "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"),
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
