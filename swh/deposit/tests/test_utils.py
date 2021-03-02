# Copyright (C) 2018-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from unittest.mock import patch

import pytest

from swh.deposit import utils
from swh.deposit.parsers import parse_xml
from swh.model.exceptions import ValidationError
from swh.model.identifiers import CoreSWHID, QualifiedSWHID


@pytest.fixture
def xml_with_origin_reference():
    xml_data = """<?xml version="1.0"?>
  <entry xmlns="http://www.w3.org/2005/Atom"
           xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0"
           xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">
      <swh:deposit>
        <swh:reference>
          <swh:origin url="{url}"/>
        </swh:reference>
      </swh:deposit>
  </entry>
    """
    return xml_data.strip()


def test_merge():
    """Calling utils.merge on dicts should merge without losing information

    """
    d0 = {"author": "someone", "license": [["gpl2"]], "a": 1}

    d1 = {
        "author": ["author0", {"name": "author1"}],
        "license": [["gpl3"]],
        "b": {"1": "2"},
    }

    d2 = {"author": map(lambda x: x, ["else"]), "license": "mit", "b": {"2": "3",}}

    d3 = {
        "author": (v for v in ["no one"]),
    }

    actual_merge = utils.merge(d0, d1, d2, d3)

    expected_merge = {
        "a": 1,
        "license": [["gpl2"], ["gpl3"], "mit"],
        "author": ["someone", "author0", {"name": "author1"}, "else", "no one"],
        "b": {"1": "2", "2": "3",},
    }
    assert actual_merge == expected_merge


def test_merge_2():
    d0 = {"license": "gpl2", "runtime": {"os": "unix derivative"}}

    d1 = {"license": "gpl3", "runtime": "GNU/Linux"}

    expected = {
        "license": ["gpl2", "gpl3"],
        "runtime": [{"os": "unix derivative"}, "GNU/Linux"],
    }

    actual = utils.merge(d0, d1)
    assert actual == expected


def test_merge_edge_cases():
    input_dict = {
        "license": ["gpl2", "gpl3"],
        "runtime": [{"os": "unix derivative"}, "GNU/Linux"],
    }
    # against empty dict
    actual = utils.merge(input_dict, {})
    assert actual == input_dict

    # against oneself
    actual = utils.merge(input_dict, input_dict, input_dict)
    assert actual == input_dict


def test_merge_one_dict():
    """Merge one dict should result in the same dict value

    """
    input_and_expected = {"anything": "really"}
    actual = utils.merge(input_and_expected)
    assert actual == input_and_expected


def test_merge_raise():
    """Calling utils.merge with any no dict argument should raise

    """
    d0 = {"author": "someone", "a": 1}

    d1 = ["not a dict"]

    with pytest.raises(ValueError):
        utils.merge(d0, d1)

    with pytest.raises(ValueError):
        utils.merge(d1, d0)

    with pytest.raises(ValueError):
        utils.merge(d1)

    assert utils.merge(d0) == d0


@patch("swh.deposit.utils.normalize_timestamp", side_effect=lambda x: x)
def test_normalize_date_0(mock_normalize):
    """When date is a list, choose the first date and normalize it

    Note: We do not test swh.model.identifiers which is already tested
    in swh.model

    """
    actual_date = utils.normalize_date(["2017-10-12", "date1"])

    expected_date = "2017-10-12 00:00:00+00:00"

    assert str(actual_date) == expected_date


@patch("swh.deposit.utils.normalize_timestamp", side_effect=lambda x: x)
def test_normalize_date_1(mock_normalize):
    """Providing a date in a reasonable format, everything is fine

    Note: We do not test swh.model.identifiers which is already tested
    in swh.model

    """
    actual_date = utils.normalize_date("2018-06-11 17:02:02")

    expected_date = "2018-06-11 17:02:02+00:00"

    assert str(actual_date) == expected_date


@patch("swh.deposit.utils.normalize_timestamp", side_effect=lambda x: x)
def test_normalize_date_doing_irrelevant_stuff(mock_normalize):
    """Providing a date with only the year results in a reasonable date

    Note: We do not test swh.model.identifiers which is already tested
    in swh.model

    """
    actual_date = utils.normalize_date("2017")

    expected_date = "2017-01-01 00:00:00+00:00"

    assert str(actual_date) == expected_date


@pytest.mark.parametrize(
    "swhid,expected_metadata_context",
    [
        ("swh:1:cnt:51b5c8cc985d190b5a7ef4878128ebfdc2358f49", {"origin": None},),
        (
            "swh:1:snp:51b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=http://blah",
            {"origin": "http://blah", "path": None},
        ),
        (
            "swh:1:dir:51b5c8cc985d190b5a7ef4878128ebfdc2358f49;path=/path",
            {"origin": None, "path": b"/path"},
        ),
        (
            "swh:1:rev:51b5c8cc985d190b5a7ef4878128ebfdc2358f49;visit=swh:1:snp:41b5c8cc985d190b5a7ef4878128ebfdc2358f49",  # noqa
            {
                "origin": None,
                "path": None,
                "snapshot": CoreSWHID.from_string(
                    "swh:1:snp:41b5c8cc985d190b5a7ef4878128ebfdc2358f49"
                ),
            },
        ),
        (
            "swh:1:rel:51b5c8cc985d190b5a7ef4878128ebfdc2358f49;anchor=swh:1:dir:41b5c8cc985d190b5a7ef4878128ebfdc2358f49",  # noqa
            {
                "origin": None,
                "path": None,
                "directory": CoreSWHID.from_string(
                    "swh:1:dir:41b5c8cc985d190b5a7ef4878128ebfdc2358f49"
                ),
            },
        ),
    ],
)
def test_compute_metadata_context(swhid: str, expected_metadata_context):
    assert expected_metadata_context == utils.compute_metadata_context(
        QualifiedSWHID.from_string(swhid)
    )


def test_parse_swh_reference_origin(xml_with_origin_reference):
    url = "https://url"
    xml_data = xml_with_origin_reference.format(url=url)
    metadata = parse_xml(xml_data)

    actual_origin = utils.parse_swh_reference(metadata)
    assert actual_origin == url


@pytest.fixture
def xml_with_empty_reference():
    xml_data = """<?xml version="1.0"?>
  <entry xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit">
      <swh:deposit>
        {swh_reference}
      </swh:deposit>
  </entry>
    """
    return xml_data.strip()


@pytest.mark.parametrize(
    "xml_ref",
    [
        "",
        "<swh:reference></swh:reference>",
        "<swh:reference><swh:object /></swh:reference>",
        """<swh:reference><swh:object swhid="" /></swh:reference>""",
    ],
)
def test_parse_swh_reference_empty(xml_with_empty_reference, xml_ref):
    xml_body = xml_with_empty_reference.format(swh_reference=xml_ref)
    metadata = utils.parse_xml(xml_body)

    assert utils.parse_swh_reference(metadata) is None


@pytest.fixture
def xml_with_swhid(atom_dataset):
    return atom_dataset["entry-data-with-swhid"]


@pytest.mark.parametrize(
    "swhid",
    [
        "swh:1:cnt:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=https://hal.archives-ouvertes.fr/hal-01243573;visit=swh:1:snp:4fc1e36fca86b2070204bedd51106014a614f321;anchor=swh:1:rev:9c5de20cfb54682370a398fcc733e829903c8cba;path=/moranegg-AffectationRO-df7f68b/",  # noqa
        "swh:1:dir:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;anchor=swh:1:dir:9c5de20cfb54682370a398fcc733e829903c8cba",  # noqa
        "swh:1:rev:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;anchor=swh:1:rev:9c5de20cfb54682370a398fcc733e829903c8cba",  # noqa
        "swh:1:rel:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;anchor=swh:1:rel:9c5de20cfb54682370a398fcc733e829903c8cba",  # noqa
        "swh:1:snp:31b5c8cc985d190b5a7ef4878128ebfdc2358f49;anchor=swh:1:snp:9c5de20cfb54682370a398fcc733e829903c8cba",  # noqa
        "swh:1:dir:31b5c8cc985d190b5a7ef4878128ebfdc2358f49",
    ],
)
def test_parse_swh_reference_swhid(swhid, xml_with_swhid):
    xml_data = xml_with_swhid.format(swhid=swhid)
    metadata = utils.parse_xml(xml_data)

    actual_swhid = utils.parse_swh_reference(metadata)
    assert actual_swhid is not None

    expected_swhid = QualifiedSWHID.from_string(swhid)
    assert actual_swhid == expected_swhid


@pytest.mark.parametrize(
    "invalid_swhid",
    [
        # incorrect length
        "swh:1:cnt:31b5c8cc985d190b5a7ef4878128ebfdc235"  # noqa
        # visit qualifier should be a core SWHID with type,
        "swh:1:dir:c4993c872593e960dc84e4430dbbfbc34fd706d0;visit=swh:1:rev:0175049fc45055a3824a1675ac06e3711619a55a",  # noqa
        # anchor qualifier should be a core SWHID with type one of
        "swh:1:rev:c4993c872593e960dc84e4430dbbfbc34fd706d0;anchor=swh:1:cnt:b5f505b005435fa5c4fa4c279792bd7b17167c04;path=/",  # noqa
        "swh:1:rev:c4993c872593e960dc84e4430dbbfbc34fd706d0;visit=swh:1:snp:0175049fc45055a3824a1675ac06e3711619a55a;anchor=swh:1:snp:b5f505b005435fa5c4fa4c279792bd7b17167c04",  # noqa
    ],
)
def test_parse_swh_reference_invalid_swhid(invalid_swhid, xml_with_swhid):
    """Unparsable swhid should raise

    """
    xml_invalid_swhid = xml_with_swhid.format(swhid=invalid_swhid)
    metadata = utils.parse_xml(xml_invalid_swhid)

    with pytest.raises(ValidationError):
        utils.parse_swh_reference(metadata)
