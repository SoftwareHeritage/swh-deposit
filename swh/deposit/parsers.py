# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


"""Module in charge of defining parsers with SWORD 2.0 supported mediatypes.

"""

import logging
from typing import Dict, Optional, Union
from xml.parsers.expat import ExpatError

from django.conf import settings
from rest_framework.parsers import BaseParser, FileUploadParser, MultiPartParser
import xmltodict

from swh.deposit.errors import ParserError
from swh.model.exceptions import ValidationError
from swh.model.identifiers import (
    DIRECTORY,
    RELEASE,
    REVISION,
    SNAPSHOT,
    SWHID,
    parse_swhid,
)

logger = logging.getLogger(__name__)


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
            "https://www.softwareheritage.org/schema/2018/deposit": "swh",
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


ALLOWED_QUALIFIERS_NODE_TYPE = (SNAPSHOT, REVISION, RELEASE, DIRECTORY)


def parse_swh_reference(metadata: Dict) -> Optional[Union[str, SWHID]]:
    """Parse swh reference within the metadata dict (or origin) reference if found, None
    otherwise.

    <swh:deposit>
      <swh:reference>
        <swh:origin url='https://github.com/user/repo'/>
      </swh:reference>
    </swh:deposit>

    or:

    <swh:deposit>
      <swh:reference>
        <swh:object swhid="swh:1:dir:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=https://hal.archives-ouvertes.fr/hal-01243573;visit=swh:1:snp:4fc1e36fca86b2070204bedd51106014a614f321;anchor=swh:1:rev:9c5de20cfb54682370a398fcc733e829903c8cba;path=/moranegg-AffectationRO-df7f68b/"
      />
    </swh:deposit>

    Raises:
        ValidationError in case the swhid referenced (if any) is invalid

    Returns:
        Either swhid or origin reference if any. None otherwise.

    """  # noqa
    visit_swhid = None
    anchor_swhid = None

    swh_deposit = metadata.get("swh:deposit")
    if not swh_deposit:
        return None

    swh_reference = swh_deposit.get("swh:reference")
    if not swh_reference:
        return None

    swh_origin = swh_reference.get("swh:origin")
    if swh_origin:
        url = swh_origin.get("@url")
        if url:
            return url

    swh_object = swh_reference.get("swh:object")
    if not swh_object:
        return None

    swhid = swh_object.get("@swhid")
    if not swhid:
        return None
    swhid_reference = parse_swhid(swhid)

    if swhid_reference.metadata:
        anchor = swhid_reference.metadata.get("anchor")
        if anchor:
            anchor_swhid = parse_swhid(anchor)
            if anchor_swhid.object_type not in ALLOWED_QUALIFIERS_NODE_TYPE:
                error_msg = (
                    "anchor qualifier should be a core SWHID with type one of "
                    f" {', '.join(ALLOWED_QUALIFIERS_NODE_TYPE)}"
                )
                raise ValidationError(error_msg)

        visit = swhid_reference.metadata.get("visit")
        if visit:
            visit_swhid = parse_swhid(visit)
            if visit_swhid.object_type != SNAPSHOT:
                raise ValidationError(
                    f"visit qualifier should be a core SWHID with type {SNAPSHOT}"
                )

        if (
            visit_swhid
            and anchor_swhid
            and visit_swhid.object_type == SNAPSHOT
            and anchor_swhid.object_type == SNAPSHOT
        ):
            logger.warn(
                "SWHID use of both anchor and visit targeting "
                f"a snapshot: {swhid_reference}"
            )
            raise ValidationError(
                "'anchor=swh:1:snp:' is not supported when 'visit' is also provided."
            )

    return swhid_reference
