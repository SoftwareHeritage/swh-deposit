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

# from https://datatracker.ietf.org/doc/html/rfc4287
ATOM_ELEMENTS = [
    "name",
    "uri",
    "email",
    # specifically not allowing this one, because clients are supposed to send one
    # entry at a time:
    # "feed",
    "entry",
    # ditto:
    # "content",
    "author",
    "category",
    "contributor",
    "generator",
    "icon",
    "id",
    "link",
    "logo",
    "published",
    "rights",
    "source",
    "subtitle",
    "summary",
    "title",
    "updated",
]

# from https://github.com/codemeta/codemeta/blob/2.0/codemeta.jsonld
CODEMETA2_CONTEXT = {
    "type": "@type",
    "id": "@id",
    "schema": "http://schema.org/",
    "codemeta": "https://codemeta.github.io/terms/",
    "Organization": {"@id": "schema:Organization"},
    "Person": {"@id": "schema:Person"},
    "SoftwareSourceCode": {"@id": "schema:SoftwareSourceCode"},
    "SoftwareApplication": {"@id": "schema:SoftwareApplication"},
    "Text": {"@id": "schema:Text"},
    "URL": {"@id": "schema:URL"},
    "address": {"@id": "schema:address"},
    "affiliation": {"@id": "schema:affiliation"},
    "applicationCategory": {"@id": "schema:applicationCategory", "@type": "@id"},
    "applicationSubCategory": {"@id": "schema:applicationSubCategory", "@type": "@id"},
    "citation": {"@id": "schema:citation"},
    "codeRepository": {"@id": "schema:codeRepository", "@type": "@id"},
    "contributor": {"@id": "schema:contributor"},
    "copyrightHolder": {"@id": "schema:copyrightHolder"},
    "copyrightYear": {"@id": "schema:copyrightYear"},
    "creator": {"@id": "schema:creator"},
    "dateCreated": {"@id": "schema:dateCreated", "@type": "schema:Date"},
    "dateModified": {"@id": "schema:dateModified", "@type": "schema:Date"},
    "datePublished": {"@id": "schema:datePublished", "@type": "schema:Date"},
    "description": {"@id": "schema:description"},
    "downloadUrl": {"@id": "schema:downloadUrl", "@type": "@id"},
    "email": {"@id": "schema:email"},
    "editor": {"@id": "schema:editor"},
    "encoding": {"@id": "schema:encoding"},
    "familyName": {"@id": "schema:familyName"},
    "fileFormat": {"@id": "schema:fileFormat", "@type": "@id"},
    "fileSize": {"@id": "schema:fileSize"},
    "funder": {"@id": "schema:funder"},
    "givenName": {"@id": "schema:givenName"},
    "hasPart": {"@id": "schema:hasPart"},
    "identifier": {"@id": "schema:identifier", "@type": "@id"},
    "installUrl": {"@id": "schema:installUrl", "@type": "@id"},
    "isAccessibleForFree": {"@id": "schema:isAccessibleForFree"},
    "isPartOf": {"@id": "schema:isPartOf"},
    "keywords": {"@id": "schema:keywords"},
    "license": {"@id": "schema:license", "@type": "@id"},
    "memoryRequirements": {"@id": "schema:memoryRequirements", "@type": "@id"},
    "name": {"@id": "schema:name"},
    "operatingSystem": {"@id": "schema:operatingSystem"},
    "permissions": {"@id": "schema:permissions"},
    "position": {"@id": "schema:position"},
    "processorRequirements": {"@id": "schema:processorRequirements"},
    "producer": {"@id": "schema:producer"},
    "programmingLanguage": {"@id": "schema:programmingLanguage"},
    "provider": {"@id": "schema:provider"},
    "publisher": {"@id": "schema:publisher"},
    "relatedLink": {"@id": "schema:relatedLink", "@type": "@id"},
    "releaseNotes": {"@id": "schema:releaseNotes", "@type": "@id"},
    "runtimePlatform": {"@id": "schema:runtimePlatform"},
    "sameAs": {"@id": "schema:sameAs", "@type": "@id"},
    "softwareHelp": {"@id": "schema:softwareHelp"},
    "softwareRequirements": {"@id": "schema:softwareRequirements", "@type": "@id"},
    "softwareVersion": {"@id": "schema:softwareVersion"},
    "sponsor": {"@id": "schema:sponsor"},
    "storageRequirements": {"@id": "schema:storageRequirements", "@type": "@id"},
    "supportingData": {"@id": "schema:supportingData"},
    "targetProduct": {"@id": "schema:targetProduct"},
    "url": {"@id": "schema:url", "@type": "@id"},
    "version": {"@id": "schema:version"},
    "author": {"@id": "schema:author", "@container": "@list"},
    "softwareSuggestions": {"@id": "codemeta:softwareSuggestions", "@type": "@id"},
    "contIntegration": {"@id": "codemeta:contIntegration", "@type": "@id"},
    "buildInstructions": {"@id": "codemeta:buildInstructions", "@type": "@id"},
    "developmentStatus": {"@id": "codemeta:developmentStatus", "@type": "@id"},
    "embargoDate": {"@id": "codemeta:embargoDate", "@type": "schema:Date"},
    "funding": {"@id": "codemeta:funding"},
    "readme": {"@id": "codemeta:readme", "@type": "@id"},
    "issueTracker": {"@id": "codemeta:issueTracker", "@type": "@id"},
    "referencePublication": {"@id": "codemeta:referencePublication", "@type": "@id"},
    "maintainer": {"@id": "codemeta:maintainer"},
}


def extra_validator(
    element: ElementTree.Element,
    xsd_element: xmlschema.validators.elements.Xsd11Element,
) -> Iterator[xmlschema.XMLSchemaValidationError]:
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
    if metadata.tag != "{http://www.w3.org/2005/Atom}entry":
        return False, {
            "metadata": [
                {
                    "fields": ["atom:entry"],
                    "summary": (
                        "Root element should be {http://www.w3.org/2005/Atom}entry, "
                        f"but it is {metadata.tag}"
                    ),
                }
            ]
        }

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

    for element in metadata.iter():
        if element.tag.startswith("{http://www.w3.org/2005/Atom}"):
            _, local_name = element.tag.split("}", 1)
            if local_name not in ATOM_ELEMENTS:
                if local_name == "external_identifier":
                    detail.append(
                        {
                            "fields": [local_name],
                            "summary": "<external_identifier> is not supported anymore, "
                            "<swh:create_origin> or <swh:add_to_origin> should be used "
                            "instead.",
                        }
                    )
                elif local_name in CODEMETA2_CONTEXT:
                    # Probably confused the two namespaces, display a nicer error
                    detail.append(
                        {
                            "fields": [local_name],
                            "summary": f"{local_name} is not a valid Atom element. "
                            "However, it would be a valid a Codemeta term; make sure "
                            "namespaces are not swapped",
                        }
                    )
                else:
                    detail.append(
                        {
                            "fields": [local_name],
                            "summary": f"{local_name} is not a valid Atom element, "
                            "see https://datatracker.ietf.org/doc/html/rfc4287",
                        }
                    )
        elif element.tag.startswith("{https://doi.org/10.5063/SCHEMA/CODEMETA-2.0}"):
            _, local_name = element.tag.split("}", 1)
            if local_name not in CODEMETA2_CONTEXT:
                if local_name in CODEMETA2_CONTEXT:
                    # Probably confused the two namespaces, display a nicer error
                    detail.append(
                        {
                            "fields": [local_name],
                            "summary": f"{local_name} is not a valid Codemeta 2.0 term. "
                            "However, it would be a valid Atom element; make sure "
                            "namespaces are not swapped",
                        }
                    )
                else:
                    detail.append(
                        {
                            "fields": [local_name],
                            "summary": f"{local_name} is not a valid Codemeta 2.0 term, "
                            "see "
                            "https://github.com/codemeta/codemeta/blob/2.0/codemeta.jsonld",
                        }
                    )

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
