# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""Module in charge of defining parsers with SWORD 2.0 supported mediatypes.

"""

from collections import defaultdict
from decimal import Decimal
from rest_framework.parsers import FileUploadParser
from rest_framework.parsers import MultiPartParser
from rest_framework_xml.parsers import XMLParser


class SWHFileUploadZipParser(FileUploadParser):
    """File upload parser limited to zip archive.

    """
    media_type = 'application/zip'


class SWHFileUploadTarParser(FileUploadParser):
    """File upload parser limited to zip archive.

    """
    media_type = 'application/x-tar'


class ListXMLParser(XMLParser):
    """Patch XMLParser behavior to not merge duplicated key entries.

    """
    # special tags that must be cast to list
    _tags = [
        '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}license',
        '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}programmingLanguage',
        '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}runtimePlatform',
        '{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}author',
    ]

    # converted tags to list
    _lists = None

    def __init__(self):
        self._reset()

    def _reset(self):
        self._lists = defaultdict(list)

    def parse(self, stream, media_type=None, parser_context=None):
        data = super().parse(
            stream, media_type=media_type, parser_context=parser_context)
        # Update the special values
        for key, value in self._lists.items():
            data[key] = value
        self._reset()

        return data

    def _xml_convert(self, element):
        children = list(element)
        if len(children) == 0:
            data = self._type_convert(element.text)
            if element.tag in self._tags:
                if data not in self._lists[element.tag]:
                    self._lists[element.tag].append(data)
            return data

        # if the first child tag is list-item, it means all
        # children are list-item
        if children[0].tag == "list-item":
            data = []
            for child in children:
                data.append(self._xml_convert(child))
            return data

        data = {}
        for child in children:
            data[child.tag] = self._xml_convert(child)

        if element.tag in self._tags:
            if data not in self._lists[element.tag]:
                self._lists[element.tag].append(data)

        return data


class SWHXMLParser(ListXMLParser):
    def _type_convert(self, value):
        """Override the default type converter to avoid having decimal in the
        resulting output.

        """
        value = super()._type_convert(value)
        if isinstance(value, Decimal):
            value = str(value)

        return value


class SWHAtomEntryParser(SWHXMLParser):
    """Atom entry parser limited to specific mediatype

    """
    media_type = 'application/atom+xml;type=entry'


class SWHMultiPartParser(MultiPartParser):
    """Multipart parser limited to a subset of mediatypes.

    """
    media_type = 'multipart/*; *'


def parse_xml(raw_content):
    """Parse xml body.

    Args:
        raw_content (bytes): The content to parse

    Returns:
        content parsed as dict.

    """
    return SWHXMLParser().parse(raw_content)
