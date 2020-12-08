# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Tests the handling of the Atom content when doing a POST Col-IRI."""

from io import BytesIO
import uuid

from django.urls import reverse
import pytest
from rest_framework import status

from swh.deposit.config import COL_IRI, DEPOSIT_STATUS_DEPOSITED
from swh.deposit.models import Deposit, DepositCollection, DepositRequest
from swh.deposit.parsers import parse_xml


def test_post_deposit_atom_201_even_with_decimal(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting an initial atom entry should return 201 with deposit receipt

    """
    atom_error_with_decimal = atom_dataset["error-with-decimal"]

    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
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
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
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
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
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
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
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
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-with-both-create-origin-and-add-to-origin"],
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        b"&lt;swh:create_origin&gt; and &lt;swh:add_to_origin&gt; "
        b"are mutually exclusive"
    ) in response.content


def test_add_deposit_with_add_to_origin_and_external_identifier(
    authenticated_client,
    deposit_collection,
    completed_deposit,
    atom_dataset,
    deposit_user,
):
    """Posting deposit with <swh:add_to_origin> creates a new deposit with parent

    """
    # given multiple deposit already loaded
    origin_url = deposit_user.provider_url + completed_deposit.external_id

    # adding a new deposit with the same external id as a completed deposit
    # creates the parenting chain
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-with-both-add-to-origin-and-external-id"]
        % origin_url,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"&lt;external_identifier&gt; is deprecated." in response.content


def test_post_deposit_atom_403_create_wrong_origin_url_prefix(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """Creating an origin for a prefix not owned by the client is forbidden

    """
    origin_url = "http://example.org/foo"

    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data0"] % origin_url,
        HTTP_IN_PROGRESS="true",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    expected_msg = (
        f"Cannot create origin {origin_url}, "
        f"it must start with {deposit_user.provider_url}"
    )
    assert expected_msg in response.content.decode()


def test_post_deposit_atom_403_add_to_wrong_origin_url_prefix(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """Creating an origin for a prefix not owned by the client is forbidden

    """
    origin_url = "http://example.org/foo"

    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-with-add-to-origin"] % origin_url,
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
    response = authenticated_client.post(
        url,
        content_type="application/atom+xml;type=entry",
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
    response = authenticated_client.post(
        url,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-no-origin-url"],
        # + headers
        HTTP_IN_PROGRESS="false",
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
    response = authenticated_client.post(
        url,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["error-with-external-identifier"] % external_id,
        # + headers
        HTTP_IN_PROGRESS="false",
        HTTP_SLUG="something",
    )

    assert b"The &#39;external_identifier&#39; tag is deprecated" in response.content
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
    response = authenticated_client.post(
        url,
        content_type="application/atom+xml;type=entry",
        data=document,
        # + headers
        HTTP_IN_PROGRESS="false",
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
    response = authenticated_client.post(
        url,
        content_type="application/atom+xml;type=entry",
        data=document,
        # + headers
        HTTP_IN_PROGRESS="false",
    )

    assert b"only one may be used on a given deposit" in response.content
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_deposit_atom_unknown_collection(authenticated_client, atom_dataset):
    """Posting an atom entry to an unknown collection should return a 404

    """
    unknown_collection = "unknown-one"
    with pytest.raises(DepositCollection.DoesNotExist):
        DepositCollection.objects.get(name=unknown_collection)

    response = authenticated_client.post(
        reverse(COL_IRI, args=[unknown_collection]),  # <- unknown collection
        content_type="application/atom+xml;type=entry",
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
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
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
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
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


def test_post_deposit_atom_entry_multiple_steps(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """After initial deposit, updating a deposit should return a 201

    """
    # given
    origin_url = deposit_user.provider_url + "2225c695-cfb8-4ebb-aaaa-80da344efa6a"

    with pytest.raises(Deposit.DoesNotExist):
        deposit = Deposit.objects.get(origin_url=origin_url)

    # when
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data1"],
        HTTP_IN_PROGRESS="True",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = int(response_content["swh:deposit_id"])

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.origin_url is None  # not provided yet
    assert deposit.status == "partial"

    # one associated request to a deposit
    deposit_requests = DepositRequest.objects.filter(deposit=deposit)
    assert len(deposit_requests) == 1

    atom_entry_data = atom_dataset["entry-only-create-origin"] % (origin_url)

    for link in response_content["atom:link"]:
        if link["@rel"] == "http://purl.org/net/sword/terms/add":
            se_iri = link["@href"]
            break
    else:
        assert False, f"missing SE-IRI from {response_content['link']}"

    # when updating the first deposit post
    response = authenticated_client.post(
        se_iri,
        content_type="application/atom+xml;type=entry",
        data=atom_entry_data,
        HTTP_IN_PROGRESS="False",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED, response.content.decode()

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = int(response_content["swh:deposit_id"])

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.origin_url == origin_url
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    assert len(Deposit.objects.all()) == 1

    # now 2 associated requests to a same deposit
    deposit_requests = DepositRequest.objects.filter(deposit=deposit).order_by("id")
    assert len(deposit_requests) == 2

    atom_entry_data1 = atom_dataset["entry-data1"]
    expected_meta = [
        {"metadata": parse_xml(atom_entry_data1), "raw_metadata": atom_entry_data1},
        {"metadata": parse_xml(atom_entry_data), "raw_metadata": atom_entry_data},
    ]

    for i, deposit_request in enumerate(deposit_requests):
        actual_metadata = deposit_request.metadata
        assert actual_metadata == expected_meta[i]["metadata"]
        assert deposit_request.raw_metadata == expected_meta[i]["raw_metadata"]
        assert bool(deposit_request.archive) is False
