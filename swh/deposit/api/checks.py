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

MANDATORY_FIELDS_MISSING = "Mandatory fields are missing"
ALTERNATE_FIELDS_MISSING = "Mandatory alternate fields are missing"


def check_metadata(metadata: Dict) -> Tuple[bool, Optional[Dict]]:
    """Check metadata for mandatory field presence.

    Args:
        metadata: Metadata dictionary to check for mandatory fields

    Returns:
        tuple (status, error_detail): True, None if metadata are
          ok (False, <detailed-error>) otherwise.

    """
    # following fields are mandatory
    required_fields = {
        "author": False,
    }
    # at least one value per couple below is mandatory
    alternate_fields = {
        ("name", "title"): False,
    }

    for field, value in metadata.items():
        for name in required_fields:
            if name in field:
                required_fields[name] = True

        for possible_names in alternate_fields:
            for possible_name in possible_names:
                if possible_name in field:
                    alternate_fields[possible_names] = True
                    continue

    mandatory_result = [k for k, v in required_fields.items() if not v]
    optional_result = [" or ".join(k) for k, v in alternate_fields.items() if not v]

    if mandatory_result == [] and optional_result == []:
        return True, None
    detail = []
    if mandatory_result != []:
        detail.append({"summary": MANDATORY_FIELDS_MISSING, "fields": mandatory_result})
    if optional_result != []:
        detail.append(
            {"summary": ALTERNATE_FIELDS_MISSING, "fields": optional_result,}
        )
    return False, {"metadata": detail}
