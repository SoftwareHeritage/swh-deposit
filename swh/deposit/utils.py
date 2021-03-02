# Copyright (C) 2018-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from types import GeneratorType
from typing import Any, Dict, Optional, Union

import iso8601
import xmltodict

from swh.model.exceptions import ValidationError
from swh.model.identifiers import (
    ExtendedSWHID,
    ObjectType,
    QualifiedSWHID,
    normalize_timestamp,
)

logger = logging.getLogger(__name__)


def parse_xml(stream, encoding="utf-8"):
    namespaces = {
        "http://www.w3.org/2005/Atom": "atom",
        "http://www.w3.org/2007/app": "app",
        "http://purl.org/dc/terms/": "dc",
        "https://doi.org/10.5063/SCHEMA/CODEMETA-2.0": "codemeta",
        "http://purl.org/net/sword/terms/": "sword",
        "https://www.softwareheritage.org/schema/2018/deposit": "swh",
    }

    data = xmltodict.parse(
        stream,
        encoding=encoding,
        namespaces=namespaces,
        process_namespaces=True,
        dict_constructor=dict,
    )
    if "atom:entry" in data:
        data = data["atom:entry"]
    return data


def merge(*dicts):
    """Given an iterator of dicts, merge them losing no information.

    Args:
        *dicts: arguments are all supposed to be dict to merge into one

    Returns:
        dict merged without losing information

    """

    def _extend(existing_val, value):
        """Given an existing value and a value (as potential lists), merge
           them together without repetition.

        """
        if isinstance(value, (list, map, GeneratorType)):
            vals = value
        else:
            vals = [value]
        for v in vals:
            if v in existing_val:
                continue
            existing_val.append(v)
        return existing_val

    d = {}
    for data in dicts:
        if not isinstance(data, dict):
            raise ValueError("dicts is supposed to be a variable arguments of dict")

        for key, value in data.items():
            existing_val = d.get(key)
            if not existing_val:
                d[key] = value
                continue
            if isinstance(existing_val, (list, map, GeneratorType)):
                new_val = _extend(existing_val, value)
            elif isinstance(existing_val, dict):
                if isinstance(value, dict):
                    new_val = merge(existing_val, value)
                else:
                    new_val = _extend([existing_val], value)
            else:
                new_val = _extend([existing_val], value)
            d[key] = new_val
    return d


def normalize_date(date):
    """Normalize date fields as expected by swh workers.

    If date is a list, elect arbitrarily the first element of that
    list

    If date is (then) a string, parse it through
    dateutil.parser.parse to extract a datetime.

    Then normalize it through
    swh.model.identifiers.normalize_timestamp.

    Returns
        The swh date object

    """
    if isinstance(date, list):
        date = date[0]
    if isinstance(date, str):
        date = iso8601.parse_date(date)

    return normalize_timestamp(date)


def compute_metadata_context(swhid_reference: QualifiedSWHID) -> Dict[str, Any]:
    """Given a SWHID object, determine the context as a dict.

    """
    metadata_context: Dict[str, Any] = {"origin": None}
    if swhid_reference.qualifiers():
        metadata_context = {
            "origin": swhid_reference.origin,
            "path": swhid_reference.path,
        }
        snapshot = swhid_reference.visit
        if snapshot:
            metadata_context["snapshot"] = snapshot

        anchor = swhid_reference.anchor
        if anchor:
            metadata_context[anchor.object_type.name.lower()] = anchor

    return metadata_context


ALLOWED_QUALIFIERS_NODE_TYPE = (
    ObjectType.SNAPSHOT,
    ObjectType.REVISION,
    ObjectType.RELEASE,
    ObjectType.DIRECTORY,
)


def parse_swh_reference(metadata: Dict,) -> Optional[Union[QualifiedSWHID, str]]:
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
    swhid_reference = QualifiedSWHID.from_string(swhid)

    if swhid_reference.qualifiers():
        anchor = swhid_reference.anchor
        if anchor:
            if anchor.object_type not in ALLOWED_QUALIFIERS_NODE_TYPE:
                error_msg = (
                    "anchor qualifier should be a core SWHID with type one of "
                    f"{', '.join(t.name.lower() for t in ALLOWED_QUALIFIERS_NODE_TYPE)}"
                )
                raise ValidationError(error_msg)

        visit = swhid_reference.visit
        if visit:
            if visit.object_type != ObjectType.SNAPSHOT:
                raise ValidationError(
                    f"visit qualifier should be a core SWHID with type snp, "
                    f"not {visit.object_type.value}"
                )

        if (
            visit
            and anchor
            and visit.object_type == ObjectType.SNAPSHOT
            and anchor.object_type == ObjectType.SNAPSHOT
        ):
            logger.warn(
                "SWHID use of both anchor and visit targeting "
                f"a snapshot: {swhid_reference}"
            )
            raise ValidationError(
                "'anchor=swh:1:snp:' is not supported when 'visit' is also provided."
            )

    return swhid_reference


def extended_swhid_from_qualified(swhid: QualifiedSWHID) -> ExtendedSWHID:
    """Used to get the target of a metadata object from a <swh:reference>,
    as the latter uses a QualifiedSWHID."""
    return ExtendedSWHID.from_string(str(swhid).split(";")[0])
