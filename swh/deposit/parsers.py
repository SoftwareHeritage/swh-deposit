# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""Module in charge of defining parsers with SWORD 2.0 supported mediatypes.

"""

from xml.parsers.expat import ExpatError

from django.conf import settings
from rest_framework.parsers import BaseParser, FileUploadParser, MultiPartParser
import xmltodict

from swh.deposit.errors import ParserError


class SWHFileUploadZipParser(FileUploadParser):
    """File upload parser limited to zip archive.

    """

    media_type = "application/zip"


class SWHFileUploadTarParser(FileUploadParser):
    """File upload parser limited to tarball (tar, tar.gz, tar.*) archives.

    """

    media_type = "application/x-tar"


class SWHXMLParser(BaseParser):
    """
    XML parser.
    """

    media_type = "application/xml"

    def parse(self, stream, media_type=None, parser_context=None):
        """
        Parses the incoming bytestream as XML and returns the resulting data.
        """
        parser_context = parser_context or {}
        encoding = parser_context.get("encoding", settings.DEFAULT_CHARSET)
        namespaces = {
            "http://www.w3.org/2005/Atom": None,
            "http://purl.org/dc/terms/": None,
            "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0": "codemeta",
            "http://purl.org/net/sword/": "sword",
        }

        data = xmltodict.parse(
            stream, encoding=encoding, namespaces=namespaces, process_namespaces=True
        )
        if "entry" in data:
            data = data["entry"]
        return data


class SWHAtomEntryParser(SWHXMLParser):
    """Atom entry parser limited to specific mediatype

    """

    media_type = "application/atom+xml;type=entry"

    def parse(self, stream, media_type=None, parser_context=None):
        # We do not actually want to parse the stream yet
        # because we want to keep the raw data as well
        # this is done later in the atom entry call
        # (cf. swh.deposit.api.common.APIBase._atom_entry)
        return stream


class SWHMultiPartParser(MultiPartParser):
    """Multipart parser limited to a subset of mediatypes.

    """

    media_type = "multipart/*; *"


def parse_xml(raw_content):
    """Parse xml body.

    Args:
        raw_content (bytes): The content to parse

    Raises:
        ParserError in case of a malformed xml

    Returns:
        content parsed as dict.

    """
    try:
        return SWHXMLParser().parse(raw_content)
    except ExpatError as e:
        raise ParserError(str(e))
