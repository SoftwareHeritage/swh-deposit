# Copyright (C) 2017-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Functional Metadata checks:

Mandatory fields:
- 'author'
- 'name' or 'title'

Suggested fields:
- metadata-provenance

"""

from typing import Dict, Optional, Tuple
from xml.etree import ElementTree

import iso8601

from swh.deposit.utils import NAMESPACES, normalize_date, parse_swh_metadata_provenance

MANDATORY_FIELDS_MISSING = "Mandatory fields are missing"
INVALID_DATE_FORMAT = "Invalid date format"

SUGGESTED_FIELDS_MISSING = "Suggested fields are missing"
METADATA_PROVENANCE_KEY = "swh:metadata-provenance"


def check_metadata(metadata: ElementTree.Element) -> Tuple[bool, Optional[Dict]]:
    """Check metadata for mandatory field presence and date format.

    Args:
        metadata: Metadata dictionary to check

    Returns:
        tuple (status, error_detail):
          - (True, None) if metadata are ok and suggested fields are also present
          - (True, <detailed-error>) if metadata are ok but some suggestions are missing
          - (False, <detailed-error>) otherwise.

    """
    suggested_fields = []
    # at least one value per couple below is mandatory
    alternate_fields = {
        ("atom:name", "atom:title", "codemeta:name"): False,
        ("atom:author", "codemeta:author"): False,
    }

    for possible_names in alternate_fields:
        for possible_name in possible_names:
            if metadata.find(possible_name, namespaces=NAMESPACES) is not None:
                alternate_fields[possible_names] = True
                continue

    mandatory_result = [" or ".join(k) for k, v in alternate_fields.items() if not v]

    # provenance metadata is optional
    provenance_meta = parse_swh_metadata_provenance(metadata)
    if provenance_meta is None:
        suggested_fields = [
            {"summary": SUGGESTED_FIELDS_MISSING, "fields": [METADATA_PROVENANCE_KEY]}
        ]

    if mandatory_result:
        detail = [{"summary": MANDATORY_FIELDS_MISSING, "fields": mandatory_result}]
        return False, {"metadata": detail + suggested_fields}

    fields = []

    for commit_date in metadata.findall(
        "codemeta:datePublished", namespaces=NAMESPACES
    ):
        try:
            normalize_date(commit_date.text)
        except iso8601.iso8601.ParseError:
            fields.append("codemeta:datePublished")

    for author_date in metadata.findall("codemeta:dateCreated", namespaces=NAMESPACES):
        try:
            normalize_date(author_date.text)
        except iso8601.iso8601.ParseError:
            fields.append("codemeta:dateCreated")

    if fields:
        detail = [{"summary": INVALID_DATE_FORMAT, "fields": fields}]
        return False, {"metadata": detail + suggested_fields}

    if suggested_fields:  # it's fine but warn about missing suggested fields
        return True, {"metadata": suggested_fields}
    return True, None
