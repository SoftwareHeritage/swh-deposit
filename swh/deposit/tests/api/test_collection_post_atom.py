# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Tests the handling of the Atom content when doing a POST Col-IRI."""

from io import BytesIO
import uuid

import attr
from django.urls import reverse_lazy as reverse
import pytest
from rest_framework import status

from swh.deposit.config import (
    COL_IRI,
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    APIConfig,
)
from swh.deposit.models import Deposit, DepositCollection, DepositRequest
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import post_atom
from swh.deposit.utils import compute_metadata_context, extended_swhid_from_qualified
from swh.model.identifiers import QualifiedSWHID
from swh.model.model import (
    MetadataAuthority,
    MetadataAuthorityType,
    MetadataFetcher,
    Origin,
    RawExtrinsicMetadata,
)
from swh.storage.interface import PagedResult


def test_post_deposit_atom_201_even_with_decimal(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting an initial atom entry should return 201 with deposit receipt

    """
    atom_error_with_decimal = atom_dataset["error-with-decimal"]

    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_error_with_decimal,
        HTTP_SLUG="external-id",
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED, response.content.decode()

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    dr = DepositRequest.objects.get(deposit=deposit)

    assert dr.metadata is not None
    sw_version = dr.metadata.get("codemeta:softwareVersion")
    assert sw_version == "10.4"


def test_post_deposit_atom_400_with_empty_body(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting empty body request should return a 400 response

    """
    atom_content = atom_dataset["entry-data-empty-body"]
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_content,
        HTTP_SLUG="external-id",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Empty body request is not supported" in response.content


def test_post_deposit_atom_400_badly_formatted_atom(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting a badly formatted atom should return a 400 response

    """
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data-badly-formatted"],
        HTTP_SLUG="external-id",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Malformed xml metadata" in response.content


def test_post_deposit_atom_parsing_error(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting parsing error prone atom should return 400

    """
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data-parsing-error-prone"],
        HTTP_SLUG="external-id",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Malformed xml metadata" in response.content


def test_post_deposit_atom_400_both_create_origin_and_add_to_origin(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting a badly formatted atom should return a 400 response

    """
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data-with-both-create-origin-and-add-to-origin"],
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        b"&lt;swh:create_origin&gt; and &lt;swh:add_to_origin&gt; "
        b"are mutually exclusive"
    ) in response.content


def test_post_deposit_atom_403_create_wrong_origin_url_prefix(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """Creating an origin for a prefix not owned by the client is forbidden

    """
    origin_url = "http://example.org/foo"

    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data0"] % origin_url,
        HTTP_IN_PROGRESS="true",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    expected_msg = (
        f"Cannot create origin {origin_url}, "
        f"it must start with {deposit_user.provider_url}"
    )
    assert expected_msg in response.content.decode()


def test_post_deposit_atom_use_slug_header(
    authenticated_client, deposit_collection, deposit_user, atom_dataset, mocker
):
    """Posting an atom entry with a slug header but no origin url generates
    an origin url from the slug

    """
    url = reverse(COL_IRI, args=[deposit_collection.name])

    slug = str(uuid.uuid4())

    # when
    response = post_atom(
        authenticated_client,
        url,
        data=atom_dataset["entry-data-no-origin-url"],
        HTTP_IN_PROGRESS="false",
        HTTP_SLUG=slug,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.origin_url == deposit_user.provider_url + slug
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED


def test_post_deposit_atom_no_origin_url_nor_slug_header(
    authenticated_client, deposit_collection, deposit_user, atom_dataset, mocker
):
    """Posting an atom entry without an origin url or a slug header should generate one

    """
    url = reverse(COL_IRI, args=[deposit_collection.name])

    slug = str(uuid.uuid4())
    mocker.patch("uuid.uuid4", return_value=slug)

    # when
    response = post_atom(
        authenticated_client,
        url,
        data=atom_dataset["entry-data-no-origin-url"],
        HTTP_IN_PROGRESS="false",
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.origin_url == deposit_user.provider_url + slug
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED


def test_post_deposit_atom_with_slug_and_external_identifier(
    authenticated_client, deposit_collection, deposit_user, atom_dataset, mocker
):
    """Even though <external_identifier> is deprecated, it should still be
    allowed when it matches the slug, so that we don't break existing clients

    """
    url = reverse(COL_IRI, args=[deposit_collection.name])

    slug = str(uuid.uuid4())

    # when
    response = post_atom(
        authenticated_client,
        url,
        data=atom_dataset["error-with-external-identifier"] % slug,
        HTTP_IN_PROGRESS="false",
        HTTP_SLUG=slug,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.origin_url == deposit_user.provider_url + slug
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED


def test_post_deposit_atom_with_mismatched_slug_and_external_identifier(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting an atom entry with mismatched slug header and external_identifier
    should return a 400

    """
    external_id = "foobar"
    url = reverse(COL_IRI, args=[deposit_collection.name])

    # when
    response = post_atom(
        authenticated_client,
        url,
        data=atom_dataset["error-with-external-identifier"] % external_id,
        HTTP_IN_PROGRESS="false",
        HTTP_SLUG="something",
    )

    assert (
        b"The &lt;external_identifier&gt; tag and Slug header are deprecated"
        in response.content
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_deposit_atom_with_create_origin_and_external_identifier(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """<atom:external_identifier> was deprecated before <swh:create_origin>
    was introduced, clients should get an error when trying to use both

    """
    external_id = "foobar"
    origin_url = deposit_user.provider_url + external_id
    url = reverse(COL_IRI, args=[deposit_collection.name])

    document = atom_dataset["error-with-external-identifier-and-create-origin"].format(
        external_id=external_id, url=origin_url,
    )

    # when
    response = post_atom(
        authenticated_client, url, data=document, HTTP_IN_PROGRESS="false",
    )

    assert b"&lt;external_identifier&gt; is deprecated" in response.content
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_deposit_atom_with_create_origin_and_reference(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """<swh:reference> and <swh:create_origin> are mutually exclusive

    """
    external_id = "foobar"
    origin_url = deposit_user.provider_url + external_id
    url = reverse(COL_IRI, args=[deposit_collection.name])

    document = atom_dataset["error-with-reference-and-create-origin"].format(
        external_id=external_id, url=origin_url,
    )

    # when
    response = post_atom(
        authenticated_client, url, data=document, HTTP_IN_PROGRESS="false",
    )

    assert b"only one may be used on a given deposit" in response.content
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_deposit_atom_unknown_collection(authenticated_client, atom_dataset):
    """Posting an atom entry to an unknown collection should return a 404

    """
    unknown_collection = "unknown-one"
    with pytest.raises(DepositCollection.DoesNotExist):
        DepositCollection.objects.get(name=unknown_collection)

    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[unknown_collection]),
        data=atom_dataset["entry-data0"],
        HTTP_SLUG="something",
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert b"Unknown collection" in response.content


def test_post_deposit_atom_entry_initial(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """Posting an initial atom entry should return 201 with deposit receipt

    """
    # given
    origin_url = deposit_user.provider_url + "1225c695-cfb8-4ebb-aaaa-80da344efa6a"

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(origin_url=origin_url)

    atom_entry_data = atom_dataset["entry-data0"] % origin_url

    # when
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_entry_data,
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED, response.content.decode()

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.origin_url == origin_url
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    # one associated request to a deposit
    deposit_request = DepositRequest.objects.get(deposit=deposit)
    assert deposit_request.metadata is not None
    assert deposit_request.raw_metadata == atom_entry_data
    assert bool(deposit_request.archive) is False


def test_post_deposit_atom_entry_with_codemeta(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """Posting an initial atom entry should return 201 with deposit receipt

    """
    # given
    origin_url = deposit_user.provider_url + "1225c695-cfb8-4ebb-aaaa-80da344efa6a"

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(origin_url=origin_url)

    atom_entry_data = atom_dataset["codemeta-sample"] % origin_url
    # when
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_entry_data,
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))

    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.origin_url == origin_url
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    # one associated request to a deposit
    deposit_request = DepositRequest.objects.get(deposit=deposit)
    assert deposit_request.metadata is not None
    assert deposit_request.raw_metadata == atom_entry_data
    assert bool(deposit_request.archive) is False


def test_deposit_metadata_invalid(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting invalid swhid reference is bad request returned to client

    """
    invalid_swhid = "swh:1:dir :31b5c8cc985d190b5a7ef4878128ebfdc2358f49"
    xml_data = atom_dataset["entry-data-with-swhid"].format(swhid=invalid_swhid)

    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=xml_data,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Invalid SWHID reference" in response.content


def test_deposit_metadata_fails_functional_checks(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting functionally invalid metadata swhid is bad request returned to client

    """
    swhid = "swh:1:dir:31b5c8cc985d190b5a7ef4878128ebfdc2358f49"
    invalid_xml_data = atom_dataset[
        "entry-data-with-swhid-fail-metadata-functional-checks"
    ].format(swhid=swhid)

    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=invalid_xml_data,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Functional metadata checks failure" in response.content


@pytest.mark.parametrize(
    "swhid",
    [
        "swh:1:cnt:01b5c8cc985d190b5a7ef4878128ebfdc2358f49",
        "swh:1:dir:11b5c8cc985d190b5a7ef4878128ebfdc2358f49",
        "swh:1:rev:21b5c8cc985d190b5a7ef4878128ebfdc2358f49",
        "swh:1:rel:31b5c8cc985d190b5a7ef4878128ebfdc2358f49",
        "swh:1:snp:41b5c8cc985d190b5a7ef4878128ebfdc2358f49",
        "swh:1:cnt:51b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=h://g.c/o/repo",
        "swh:1:dir:c4993c872593e960dc84e4430dbbfbc34fd706d0;origin=https://inria.halpreprod.archives-ouvertes.fr/hal-01243573;visit=swh:1:snp:0175049fc45055a3824a1675ac06e3711619a55a;anchor=swh:1:rev:b5f505b005435fa5c4fa4c279792bd7b17167c04;path=/",  # noqa
        "swh:1:rev:71b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=h://g.c/o/repo",
        "swh:1:rel:81b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=h://g.c/o/repo",
        "swh:1:snp:91b5c8cc985d190b5a7ef4878128ebfdc2358f49;origin=h://g.c/o/repo",
    ],
)
def test_deposit_metadata_swhid(
    swhid, authenticated_client, deposit_collection, atom_dataset, swh_storage,
):
    """Posting a swhid reference is stored on raw extrinsic metadata storage

    """
    swhid_reference = QualifiedSWHID.from_string(swhid)
    swhid_target = extended_swhid_from_qualified(swhid_reference)

    xml_data = atom_dataset["entry-data-with-swhid"].format(swhid=swhid)
    deposit_client = authenticated_client.deposit_client

    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=xml_data,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))

    # Ensure the deposit is finalized
    deposit_id = int(response_content["swh:deposit_id"])
    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.swhid == str(swhid_target)
    assert deposit.swhid_context == str(swhid_reference)
    assert deposit.complete_date == deposit.reception_date
    assert deposit.complete_date is not None
    assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS

    # Ensure metadata stored in the metadata storage is consistent
    metadata_authority = MetadataAuthority(
        type=MetadataAuthorityType.DEPOSIT_CLIENT,
        url=deposit_client.provider_url,
        metadata={"name": deposit_client.last_name},
    )

    actual_authority = swh_storage.metadata_authority_get(
        MetadataAuthorityType.DEPOSIT_CLIENT, url=deposit_client.provider_url
    )
    assert actual_authority == metadata_authority

    config = APIConfig()
    metadata_fetcher = MetadataFetcher(
        name=config.tool["name"],
        version=config.tool["version"],
        metadata=config.tool["configuration"],
    )

    actual_fetcher = swh_storage.metadata_fetcher_get(
        config.tool["name"], config.tool["version"]
    )
    assert actual_fetcher == metadata_fetcher

    page_results = swh_storage.raw_extrinsic_metadata_get(
        swhid_target, metadata_authority
    )
    discovery_date = page_results.results[0].discovery_date

    assert len(page_results.results) == 1
    assert page_results.next_page_token is None

    metadata_context = compute_metadata_context(swhid_reference)
    assert page_results == PagedResult(
        results=[
            RawExtrinsicMetadata(
                target=swhid_target,
                discovery_date=discovery_date,
                authority=attr.evolve(metadata_authority, metadata=None),
                fetcher=attr.evolve(metadata_fetcher, metadata=None),
                format="sword-v2-atom-codemeta",
                metadata=xml_data.encode(),
                **metadata_context,
            )
        ],
        next_page_token=None,
    )
    assert deposit.complete_date == discovery_date


@pytest.mark.parametrize(
    "url", ["https://gitlab.org/user/repo", "https://whatever.else/repo",]
)
def test_deposit_metadata_origin(
    url, authenticated_client, deposit_collection, atom_dataset, swh_storage,
):
    """Posting a swhid reference is stored on raw extrinsic metadata storage

    """
    xml_data = atom_dataset["entry-data-with-origin-reference"].format(url=url)
    origin_swhid = Origin(url).swhid()
    deposit_client = authenticated_client.deposit_client
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=xml_data,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    # Ensure the deposit is finalized
    deposit_id = int(response_content["swh:deposit_id"])
    deposit = Deposit.objects.get(pk=deposit_id)
    # we got not swhid as input so we cannot have those
    assert deposit.swhid is None
    assert deposit.swhid_context is None
    assert deposit.complete_date == deposit.reception_date
    assert deposit.complete_date is not None
    assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS

    # Ensure metadata stored in the metadata storage is consistent
    metadata_authority = MetadataAuthority(
        type=MetadataAuthorityType.DEPOSIT_CLIENT,
        url=deposit_client.provider_url,
        metadata={"name": deposit_client.last_name},
    )

    actual_authority = swh_storage.metadata_authority_get(
        MetadataAuthorityType.DEPOSIT_CLIENT, url=deposit_client.provider_url
    )
    assert actual_authority == metadata_authority

    config = APIConfig()
    metadata_fetcher = MetadataFetcher(
        name=config.tool["name"],
        version=config.tool["version"],
        metadata=config.tool["configuration"],
    )

    actual_fetcher = swh_storage.metadata_fetcher_get(
        config.tool["name"], config.tool["version"]
    )
    assert actual_fetcher == metadata_fetcher

    page_results = swh_storage.raw_extrinsic_metadata_get(
        origin_swhid, metadata_authority
    )
    discovery_date = page_results.results[0].discovery_date

    assert len(page_results.results) == 1
    assert page_results.next_page_token is None

    assert page_results == PagedResult(
        results=[
            RawExtrinsicMetadata(
                target=origin_swhid,
                discovery_date=discovery_date,
                authority=attr.evolve(metadata_authority, metadata=None),
                fetcher=attr.evolve(metadata_fetcher, metadata=None),
                format="sword-v2-atom-codemeta",
                metadata=xml_data.encode(),
            )
        ],
        next_page_token=None,
    )
    assert deposit.complete_date == discovery_date
