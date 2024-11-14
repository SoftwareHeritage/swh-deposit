# Copyright (C) 2018-2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from xml.etree import ElementTree

from django.utils import timezone
import pytest

from swh.deposit import utils
from swh.deposit.models import Deposit, DepositRequest
from swh.model.exceptions import ValidationError
from swh.model.swhids import CoreSWHID, QualifiedSWHID


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


def test_normalize_date_0():
    """When date is a list, choose the first date and normalize it"""
    actual_date = utils.normalize_date(["2017-10-12", "date1"])

    assert actual_date == {
        "timestamp": {"microseconds": 0, "seconds": 1507766400},
        "offset": 0,
    }


def test_normalize_date_1():
    """Providing a date in a reasonable format, everything is fine"""
    actual_date = utils.normalize_date("2018-06-11 17:02:02")

    assert actual_date == {
        "timestamp": {"microseconds": 0, "seconds": 1528736522},
        "offset": 0,
    }


def test_normalize_date_doing_irrelevant_stuff():
    """Providing a date with only the year results in a reasonable date"""
    actual_date = utils.normalize_date("2017")

    assert actual_date == {
        "timestamp": {"seconds": 1483228800, "microseconds": 0},
        "offset": 0,
    }


@pytest.mark.parametrize(
    "swhid,expected_metadata_context",
    [
        (
            "swh:1:cnt:51b5c8cc985d190b5a7ef4878128ebfdc2358f49",
            {"origin": None},
        ),
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
    metadata = ElementTree.fromstring(xml_data)

    actual_origin = utils.parse_swh_reference(metadata)
    assert actual_origin == url


@pytest.fixture
def xml_swh_deposit_template():
    xml_data = """<?xml version="1.0"?>
  <entry xmlns:swh="https://www.softwareheritage.org/schema/2018/deposit"
         xmlns:schema="http://schema.org/">
      <swh:deposit>
        {swh_deposit}
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
def test_parse_swh_reference_empty(xml_swh_deposit_template, xml_ref):
    xml_body = xml_swh_deposit_template.format(swh_deposit=xml_ref)
    metadata = ElementTree.fromstring(xml_body)

    assert utils.parse_swh_reference(metadata) is None


@pytest.fixture
def xml_with_swhid(atom_dataset):
    return atom_dataset["entry-data-with-swhid-no-prov"]


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
    xml_data = xml_with_swhid.format(
        swhid=swhid,
    )
    metadata = ElementTree.fromstring(xml_data)

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
    """Unparsable swhid should raise"""
    xml_invalid_swhid = xml_with_swhid.format(swhid=invalid_swhid)
    metadata = ElementTree.fromstring(xml_invalid_swhid)

    with pytest.raises(ValidationError):
        utils.parse_swh_reference(metadata)


@pytest.mark.parametrize(
    "xml_ref",
    [
        "",
        "<swh:metadata-provenance></swh:metadata-provenance>",
        "<swh:metadata-provenance><schema:url /></swh:metadata-provenance>",
    ],
)
def test_parse_swh_metatada_provenance_empty(xml_swh_deposit_template, xml_ref):
    xml_body = xml_swh_deposit_template.format(swh_deposit=xml_ref)
    metadata = ElementTree.fromstring(xml_body)

    assert utils.parse_swh_metadata_provenance(metadata) is None


@pytest.fixture
def xml_with_metadata_provenance(atom_dataset):
    return atom_dataset["entry-data-with-metadata-provenance"]


def test_parse_swh_metadata_provenance2(xml_with_metadata_provenance):
    xml_data = xml_with_metadata_provenance.format(url="https://url.org/metadata/url")
    metadata = ElementTree.fromstring(xml_data)

    actual_url = utils.parse_swh_metadata_provenance(metadata)

    assert actual_url == "https://url.org/metadata/url"


@pytest.mark.parametrize(
    "tag,value,arg,expected",
    [
        ("codemeta:softwareVersion", "v1.1.1", "codemeta:softwareVersion", "v1.1.1"),
        ("releaseNotes", "changelog", "codemeta:softwareVersion", None),
    ],
)
def test_get_element_text(tag, value, arg, expected):
    xml_data = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom"
                xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
            <{tag}>{value}</{tag}>
        </entry>
    """
    metadata = ElementTree.fromstring(xml_data.format(tag=tag, value=value))

    assert utils.get_element_text(metadata, arg) == expected


def test_extract_release_data_defaults(complete_deposit):
    xml_data = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom"
                xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
        </entry>"""
    DepositRequest.objects.create(deposit=complete_deposit, raw_metadata=xml_data)
    release_data = utils.extract_release_data(complete_deposit)
    assert release_data.software_version == "1"  # the only release for this origin
    assert release_data.release_notes == ""


def test_extract_release_data_software_version(complete_deposit):
    xml_data = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom"
                xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
            <codemeta:softwareVersion>v1.1.1</codemeta:softwareVersion>
        </entry>"""
    DepositRequest.objects.create(deposit=complete_deposit, raw_metadata=xml_data)
    release_data = utils.extract_release_data(complete_deposit)
    assert release_data.software_version == "v1.1.1"


def test_extract_release_data_release_notes(complete_deposit):
    xml_data = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom"
                xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
            <codemeta:softwareVersion>v1.1.1</codemeta:softwareVersion>
            <codemeta:releaseNotes>CHANGELOG</codemeta:releaseNotes>
        </entry>"""
    DepositRequest.objects.create(deposit=complete_deposit, raw_metadata=xml_data)
    release_data = utils.extract_release_data(complete_deposit)
    assert release_data.release_notes == "CHANGELOG"


def test_extract_release_data_guess_software_version(complete_deposit):
    complete_deposit.id = None
    complete_deposit.complete_date = timezone.now()
    complete_deposit.save()  # Creates a new deposit with the same origin url

    xml_data = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom"
                xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
        </entry>"""
    DepositRequest.objects.create(deposit=complete_deposit, raw_metadata=xml_data)
    release_data = utils.extract_release_data(complete_deposit)
    assert release_data.software_version == "2"


def test_get_releases(complete_deposit):
    # the complete_deposit fixture has no software_version, it will be ignored
    no_version_deposit = complete_deposit

    # simple case: this deposit has a unique software_version and a single deposit
    # request
    deposit_v1 = Deposit.objects.get(id=complete_deposit.id)
    deposit_v1.id = None
    deposit_v1.software_version = "v1"
    deposit_v1.complete_date = timezone.now()
    deposit_v1.save()
    DepositRequest.objects.create(deposit=deposit_v1, raw_metadata="v1 metadata")

    # this deposit will not be part of our releases as it will be overwritten by
    # deposit_v2_2
    deposit_v2 = Deposit.objects.get(id=complete_deposit.id)
    deposit_v2.id = None
    deposit_v2.software_version = "v2"
    deposit_v2.complete_date = timezone.now()
    deposit_v2.save()
    DepositRequest.objects.create(deposit=deposit_v2, raw_metadata="ignored release")

    # this deposit has multiple deposit requests, only the last one is used
    deposit_v3 = Deposit.objects.get(id=complete_deposit.id)
    deposit_v3.id = None
    deposit_v3.software_version = "v3"
    deposit_v3.complete_date = timezone.now()
    deposit_v3.save()
    DepositRequest.objects.create(
        deposit=deposit_v3, raw_metadata="overwritten by the next dr"
    )
    DepositRequest.objects.create(deposit=deposit_v3, raw_metadata="this one is kept")

    # this deposit has multiple deposit requests, the one with metadata is used
    deposit_v2_2 = Deposit.objects.get(id=complete_deposit.id)
    deposit_v2_2.id = None
    deposit_v2_2.software_version = "v2"
    deposit_v2_2.complete_date = timezone.now()
    deposit_v2_2.save()
    DepositRequest.objects.create(deposit=deposit_v2_2, raw_metadata="v2 metadata")
    DepositRequest.objects.create(deposit=deposit_v2_2)

    # v0 is deposited after v2 but releases are ordered by software_version
    deposit_v0 = Deposit.objects.get(id=complete_deposit.id)
    deposit_v0.id = None
    deposit_v0.software_version = "v0"
    deposit_v0.complete_date = timezone.now()
    deposit_v0.save()

    # this deposit is not related to the others
    deposit_other_origin = Deposit.objects.get(id=complete_deposit.id)
    deposit_other_origin.id = None
    deposit_other_origin.software_version = "v4"
    deposit_other_origin.complete_date = timezone.now()
    deposit_other_origin.origin_url = "http://example.localhost/1234"
    deposit_other_origin.save()
    DepositRequest.objects.create(
        deposit=deposit_other_origin, raw_metadata="other origin"
    )

    releases = utils.get_releases(deposit_v1)

    assert len(releases) == 4

    assert no_version_deposit not in releases
    assert deposit_other_origin not in releases
    assert deposit_v2 not in releases

    # results are ordered by software_version
    assert releases[0] == deposit_v0
    assert releases[1] == deposit_v1
    assert releases[2] == deposit_v2_2
    assert releases[3] == deposit_v3
