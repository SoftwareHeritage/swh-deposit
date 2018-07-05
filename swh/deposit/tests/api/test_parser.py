# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import io

from nose.tools import istest
from rest_framework.test import APITestCase

from swh.deposit.parsers import SWHXMLParser


class ParsingTest(APITestCase):
    """Access to main entry point is ok without authentication

    """
    @istest
    def parsing_without_duplicates(self):
        xml_no_duplicate = io.BytesIO(b'''<?xml version="1.0"?>
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
    </entry>''')

        actual_result = SWHXMLParser().parse(xml_no_duplicate)
        expected_dict = {
            '{http://www.w3.org/2005/Atom}title':
            'Awesome Compiler',
            '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}author':
            [{'{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}affiliation':
              'Inria',
              '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}name':
              'author1'}],
            '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}issueTracker':
            'http://issuetracker.com',
            '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}license':
            [{'{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}name':
              'GPL3.0',
              '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}url':
              'https://opensource.org/licenses/GPL-3.0'}],
            '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}programmingLanguage':
            ['ocaml'],
            '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}runtimePlatform':
            ['Python3']
        }
        self.assertEqual(expected_dict, actual_result)

    @istest
    def parsing_with_duplicates(self):
        xml_with_duplicates = io.BytesIO(b'''<?xml version="1.0"?>
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
    </entry>''')

        actual_result = SWHXMLParser().parse(xml_with_duplicates)

        expected_dict = {
            '{http://www.w3.org/2005/Atom}title':
            'Another Compiler',
            '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}author': [
                {'{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}affiliation':
                 'Inria',
                 '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}name':
                 'author1'},
                {'{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}affiliation':
                 'Inria',
                 '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}name':
                 'author2'}],
            '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}license': [
                {'{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}name':
                 'GPL3.0',
                 '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}url':
                 'https://opensource.org/licenses/GPL-3.0'},
                {'{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}name':
                 'spdx',
                 '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}url':
                 'http://spdx.org'}],
            '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}programmingLanguage':
            [ 'ocaml', 'haskell', 'python3'],
            '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}runtimePlatform':
            ['GNU/Linux', 'Un*x'] }
        self.assertEqual(expected_dict, actual_result)
