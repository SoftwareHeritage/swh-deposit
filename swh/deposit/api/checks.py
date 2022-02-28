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

import dataclasses
import functools
from typing import Dict, Optional, Tuple
from xml.etree import ElementTree

import pkg_resources
import xmlschema

from swh.deposit.errors import FORBIDDEN, DepositError
from swh.deposit.utils import NAMESPACES, parse_swh_metadata_provenance

MANDATORY_FIELDS_MISSING = "Mandatory fields are missing"
INVALID_DATE_FORMAT = "Invalid date format"

SUGGESTED_FIELDS_MISSING = "Suggested fields are missing"
METADATA_PROVENANCE_KEY = "swh:metadata-provenance"


@dataclasses.dataclass
class Schemas:
    swh: xmlschema.XMLSchema11
    codemeta: xmlschema.XMLSchema11


@functools.lru_cache(1)
def schemas() -> Schemas:
    def load_xsd(name) -> xmlschema.XMLSchema11:
        return xmlschema.XMLSchema11(
            pkg_resources.resource_string("swh.deposit", f"xsd/{name}.xsd").decode()
        )

    return Schemas(swh=load_xsd("swh"), codemeta=load_xsd("codemeta"))


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

    deposit_elt = metadata.find("swh:deposit", namespaces=NAMESPACES)
    if deposit_elt:
        try:
            schemas().swh.validate(deposit_elt)
        except xmlschema.exceptions.XMLSchemaException as e:
            return False, {"metadata": [{"fields": ["swh:deposit"], "summary": str(e)}]}

    detail = []
    for child in metadata:
        for schema_element in schemas().codemeta.root_elements:
            if child.tag in schema_element.name:
                break
        else:
            # Tag is not specified in the schema, don't validate it
            continue
        try:
            schemas().codemeta.validate(child)
        except xmlschema.exceptions.XMLSchemaException as e:
            detail.append({"fields": [schema_element.prefixed_name], "summary": str(e)})

    if detail:
        return False, {"metadata": detail + suggested_fields}

    if suggested_fields:  # it's fine but warn about missing suggested fields
        return True, {"metadata": suggested_fields}

    return True, None


def check_url_match_provider(url: str, provider_url: str) -> None:
    """Check url matches the provider url.

    Raises DepositError in case of mismatch

    """
    provider_url = provider_url.rstrip("/") + "/"
    if not url.startswith(provider_url):
        raise DepositError(
            FORBIDDEN, f"URL mismatch: {url} must start with {provider_url}",
        )
