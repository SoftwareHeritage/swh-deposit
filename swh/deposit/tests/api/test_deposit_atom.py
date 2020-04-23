# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from django.urls import reverse
from io import BytesIO
from rest_framework import status

from swh.deposit.config import COL_IRI, DEPOSIT_STATUS_DEPOSITED
from swh.deposit.models import Deposit, DepositRequest, DepositCollection
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
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["deposit_id"]

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
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-empty-body"],
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_deposit_atom_400_badly_formatted_atom(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting a badly formatted atom should return a 400 response

    """
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-badly-formatted"],
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_deposit_atom_parsing_error(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting parsing error prone atom should return 400

    """
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-parsing-error-prone"],
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_deposit_atom_no_slug_header(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting an atom entry without a slug header should return a 400

    """
    url = reverse(COL_IRI, args=[deposit_collection.name])

    # when
    response = authenticated_client.post(
        url,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data0"],
        # + headers
        HTTP_IN_PROGRESS="false",
    )

    assert b"Missing SLUG header" in response.content
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


def test_post_deposit_atom_entry_initial(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting an initial atom entry should return 201 with deposit receipt

    """
    # given
    external_id = "urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a"

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(external_id=external_id)

    atom_entry_data = atom_dataset["entry-data0"] % external_id

    # when
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_entry_data,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.external_id == external_id
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    # one associated request to a deposit
    deposit_request = DepositRequest.objects.get(deposit=deposit)
    assert deposit_request.metadata is not None
    assert deposit_request.raw_metadata == atom_entry_data
    assert bool(deposit_request.archive) is False


def test_post_deposit_atom_entry_with_codemeta(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting an initial atom entry should return 201 with deposit receipt

    """
    # given
    external_id = "urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a"

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(external_id=external_id)

    atom_entry_data = atom_dataset["codemeta-sample"] % external_id
    # when
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_entry_data,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))

    deposit_id = response_content["deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.external_id == external_id
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    # one associated request to a deposit
    deposit_request = DepositRequest.objects.get(deposit=deposit)
    assert deposit_request.metadata is not None
    assert deposit_request.raw_metadata == atom_entry_data
    assert bool(deposit_request.archive) is False


def test_post_deposit_atom_entry_tei(
    authenticated_client, deposit_collection, atom_dataset
):
    """Posting initial atom entry as TEI should return 201 with receipt

    """
    # given
    external_id = "urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a"
    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(external_id=external_id)

    atom_entry_data = atom_dataset["tei-sample"]

    # when
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_entry_data,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.external_id == external_id
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    # one associated request to a deposit
    deposit_request = DepositRequest.objects.get(deposit=deposit)
    assert deposit_request.metadata is not None
    assert deposit_request.raw_metadata == atom_entry_data
    assert bool(deposit_request.archive) is False


def test_post_deposit_atom_entry_multiple_steps(
    authenticated_client, deposit_collection, atom_dataset
):
    """After initial deposit, updating a deposit should return a 201

    """
    # given
    external_id = "urn:uuid:2225c695-cfb8-4ebb-aaaa-80da344efa6a"

    with pytest.raises(Deposit.DoesNotExist):
        deposit = Deposit.objects.get(external_id=external_id)

    # when
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data1"],
        HTTP_IN_PROGRESS="True",
        HTTP_SLUG=external_id,
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = int(response_content["deposit_id"])

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.external_id == external_id
    assert deposit.status == "partial"

    # one associated request to a deposit
    deposit_requests = DepositRequest.objects.filter(deposit=deposit)
    assert len(deposit_requests) == 1

    atom_entry_data = atom_dataset["entry-data-minimal"] % external_id.encode(
        "utf-8"
    )  # noqa

    update_uri = response._headers["location"][1]

    # when updating the first deposit post
    response = authenticated_client.post(
        update_uri,
        content_type="application/atom+xml;type=entry",
        data=atom_entry_data,
        HTTP_IN_PROGRESS="False",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = int(response_content["deposit_id"])

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.external_id == external_id
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
