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
import re
from typing import Dict, Iterator, Optional, Tuple, cast
import urllib
from xml.etree import ElementTree

import pkg_resources
import xmlschema

from swh.deposit.errors import FORBIDDEN, DepositError
from swh.deposit.utils import NAMESPACES, parse_swh_metadata_provenance

MANDATORY_FIELDS_MISSING = "Mandatory fields are missing"
INVALID_DATE_FORMAT = "Invalid date format"

SUGGESTED_FIELDS_MISSING = "Suggested fields are missing"
METADATA_PROVENANCE_KEY = "swh:metadata-provenance"

AFFILIATION_NO_NAME = "Reason: affiliation does not have a <codemeta:name> element"


def extra_validator(
    element: ElementTree.Element,
    xsd_element: xmlschema.validators.elements.Xsd11Element,
) -> Optional[Iterator[xmlschema.XMLSchemaValidationError]]:
    """Performs extra checks on Atom elements that cannot be implemented purely
    within XML Schema.

    For now, this only checks URIs are absolute."""
    type_name = xsd_element.type.name
    if type_name == "{http://www.w3.org/2001/XMLSchema}anyURI":
        # Check their URI is absolute.
        # This could technically be implemented in the schema like this:
        #     <xsd:simpleType name="URL">
        #       <xsd:restriction base="xsd:anyURI">
        #         <!-- https://datatracker.ietf.org/doc/html/rfc2396#section-3.1 -->
        #         <xsd:pattern value="[a-zA-Z][a-zA-Z0-9+.-]*:.+" />
        #       </xsd:restriction>
        #     </xsd:simpleType>
        # However, this would give an unreadable error, so we implement it here
        # in Python instead.
        yield from absolute_uri_validator(element, xsd_element)
    elif type_name == "{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}identifierType":
        # Made-up type, that allows both absolute URIs and HAL-IDs
        if not re.match("hal-[0-9]+", element.text or ""):
            yield from absolute_uri_validator(element, xsd_element)


def absolute_uri_validator(
    element: ElementTree.Element,
    xsd_element: xmlschema.validators.elements.Xsd11Element,
) -> Iterator[xmlschema.XMLSchemaValidationError]:
    try:
        url = urllib.parse.urlparse(element.text)
    except ValueError:
        yield xmlschema.XMLSchemaValidationError(
            xsd_element,
            element,
            f"{element.text!r} is not a valid URI",
        )
    else:
        if not url.scheme or not url.netloc:
            yield xmlschema.XMLSchemaValidationError(
                xsd_element,
                element,
                f"{element.text!r} is not an absolute URI",
            )
        elif " " in url.netloc:
            # urllib is a little too permissive...
            yield xmlschema.XMLSchemaValidationError(
                xsd_element,
                element,
                f"{element.text!r} is not a valid URI",
            )


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
            schemas().swh.validate(
                deposit_elt,
                extra_validator=cast(
                    # ExtraValidatorType is a callable with "SchemaType" as second
                    # argument, but extra_validator() is actually passed Xsd11Element
                    # as second argument
                    # https://github.com/sissaschool/xmlschema/issues/291
                    xmlschema.aliases.ExtraValidatorType,
                    extra_validator,
                ),
            )
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
            schemas().codemeta.validate(
                child,
                extra_validator=cast(
                    # ExtraValidatorType is a callable with "SchemaType" as second
                    # argument, but extra_validator() is actually passed Xsd11Element
                    # as second argument
                    # https://github.com/sissaschool/xmlschema/issues/291
                    xmlschema.aliases.ExtraValidatorType,
                    extra_validator,
                ),
            )
        except xmlschema.exceptions.XMLSchemaException as e:
            detail.append({"fields": [schema_element.prefixed_name], "summary": str(e)})
        else:
            # Manually validate <codemeta:affiliation>. Unfortunately, this cannot be
            # validated by codemeta.xsd, because Codemeta has conflicting requirements:
            # 1. https://codemeta.github.io/terms/ requires it to be Text (represented
            #    by simple content), but
            # 2. https://doi.org/10.5063/SCHEMA/CODEMETA-2.0 requires it to be an
            #    Organization (represented by complex content)
            # And this is (legitimately) not representable in XML Schema.
            #
            # See https://github.com/codemeta/codemeta/pull/239 for a discussion about
            # this issue.
            for affiliation in child.findall(
                "codemeta:affiliation", namespaces=NAMESPACES
            ):
                if len(affiliation) > 0:
                    # This is a complex element (as required by
                    # https://codemeta.github.io/terms/), then we want to make sure
                    # there is at least a name.
                    if not affiliation.findtext("codemeta:name", namespaces=NAMESPACES):
                        detail.append(
                            {
                                "fields": [schema_element.prefixed_name],
                                "summary": AFFILIATION_NO_NAME,
                            }
                        )
                        break
                else:
                    # This is a simple element (as required by
                    # https://doi.org/10.5063/SCHEMA/CODEMETA-2.0)
                    if affiliation.text is None or not affiliation.text.strip():
                        # Completely empty element
                        detail.append(
                            {
                                "fields": [schema_element.prefixed_name],
                                "summary": AFFILIATION_NO_NAME,
                            }
                        )
                        break

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
            FORBIDDEN,
            f"URL mismatch: {url} must start with {provider_url}",
        )
