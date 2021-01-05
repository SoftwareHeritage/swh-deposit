# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Functional Metadata checks:

Mandatory fields:
- 'author'
- 'name' or 'title'

"""

from typing import Dict, Optional, Tuple

import iso8601

from swh.deposit.utils import normalize_date

MANDATORY_FIELDS_MISSING = "Mandatory fields are missing"
INVALID_DATE_FORMAT = "Invalid date format"


def check_metadata(metadata: Dict) -> Tuple[bool, Optional[Dict]]:
    """Check metadata for mandatory field presence and date format.

    Args:
        metadata: Metadata dictionary to check

    Returns:
        tuple (status, error_detail): True, None if metadata are
          ok (False, <detailed-error>) otherwise.

    """
    # at least one value per couple below is mandatory
    alternate_fields = {
        ("atom:name", "atom:title", "codemeta:name"): False,
        ("atom:author", "codemeta:author"): False,
    }

    for field, value in metadata.items():
        for possible_names in alternate_fields:
            if field in possible_names:
                alternate_fields[possible_names] = True
                continue

    mandatory_result = [" or ".join(k) for k, v in alternate_fields.items() if not v]

    if mandatory_result:
        detail = [{"summary": MANDATORY_FIELDS_MISSING, "fields": mandatory_result}]
        return False, {"metadata": detail}

    fields = []

    commit_date = metadata.get("codemeta:datePublished")
    author_date = metadata.get("codemeta:dateCreated")

    if commit_date:
        try:
            normalize_date(commit_date)
        except iso8601.iso8601.ParseError:
            fields.append("codemeta:datePublished")

    if author_date:
        try:
            normalize_date(author_date)
        except iso8601.iso8601.ParseError:
            fields.append("codemeta:dateCreated")

    if fields:
        detail = [{"summary": INVALID_DATE_FORMAT, "fields": fields}]
        return False, {"metadata": detail}

    return True, None
