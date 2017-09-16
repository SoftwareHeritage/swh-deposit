# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""Module in charge of defining parsers with SWORD 2.0 supported mediatypes.

"""

from rest_framework.parsers import FileUploadParser
from rest_framework.parsers import MultiPartParser
from rest_framework_xml.parsers import XMLParser


class SWHFileUploadParser(FileUploadParser):
    """File upload parser limited to zip archive.

    """
    media_type = 'application/zip'


class SWHAtomEntryParser(XMLParser):
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
    return XMLParser().parse(raw_content)
