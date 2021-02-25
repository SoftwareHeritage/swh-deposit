# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Tests updates on SE-IRI."""

from django.urls import reverse_lazy as reverse
from rest_framework import status

from swh.deposit.config import (
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_PARTIAL,
    EDIT_IRI,
    SE_IRI,
)
from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.tests.common import post_atom, post_multipart, put_multipart


def test_add_both_archive_and_metadata_to_deposit(
    authenticated_client,
    deposit_collection,
    partial_deposit_with_metadata,
    atom_dataset,
    sample_archive,
    deposit_user,
):
    """Scenario: Add both a new archive and new metadata to a partial deposit is ok

    Response: 201

    """
    deposit = partial_deposit_with_metadata
    origin_url = deposit_user.provider_url + deposit.external_id
    requests = DepositRequest.objects.filter(deposit=deposit, type="metadata")
    assert len(requests) == 1

    requests_archive0 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive0) == 1

    data_atom_entry = atom_dataset["entry-data1"]
    response = post_multipart(
        authenticated_client,
        reverse(SE_IRI, args=[deposit_collection.name, deposit.id]),
        sample_archive,
        data_atom_entry,
    )

    assert response.status_code == status.HTTP_201_CREATED
    requests = DepositRequest.objects.filter(deposit=deposit, type="metadata").order_by(
        "id"
    )

    assert len(requests) == 1 + 1, "New deposit request archive got added"
    expected_raw_meta0 = atom_dataset["entry-data0"] % origin_url
    # a new one was added
    assert requests[0].raw_metadata == expected_raw_meta0
    assert requests[1].raw_metadata == data_atom_entry

    # check we did not touch the other parts
    requests_archive1 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive1) == 1 + 1, "New deposit request metadata got added"


def test_post_metadata_empty_post_finalize_deposit_ok(
    authenticated_client,
    deposit_collection,
    partial_deposit_with_metadata,
    atom_dataset,
):
    """Empty atom post entry with header in-progress to false transitions deposit to
       'deposited' status

    Response: 200

    """
    deposit = partial_deposit_with_metadata
    assert deposit.status == DEPOSIT_STATUS_PARTIAL

    update_uri = reverse(SE_IRI, args=[deposit_collection.name, deposit.id])
    response = post_atom(
        authenticated_client, update_uri, data="", size=0, HTTP_IN_PROGRESS=False,
    )

    assert response.status_code == status.HTTP_200_OK
    deposit = Deposit.objects.get(pk=deposit.id)
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED


def test_put_update_metadata_and_archive_deposit_partial_nominal(
    tmp_path,
    authenticated_client,
    partial_deposit_with_metadata,
    deposit_collection,
    atom_dataset,
    sample_archive,
    deposit_user,
):
    """Scenario: Replace metadata and archive(s) with new ones should be ok

    Response: 204

    """
    # given
    deposit = partial_deposit_with_metadata
    origin_url = deposit_user.provider_url + deposit.external_id
    raw_metadata0 = atom_dataset["entry-data0"] % origin_url

    requests_meta = DepositRequest.objects.filter(deposit=deposit, type="metadata")
    assert len(requests_meta) == 1
    request_meta0 = requests_meta[0]
    assert request_meta0.raw_metadata == raw_metadata0

    requests_archive0 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive0) == 1

    data_atom_entry = atom_dataset["entry-data1"]
    response = put_multipart(
        authenticated_client,
        reverse(EDIT_IRI, args=[deposit_collection.name, deposit.id]),
        sample_archive,
        data_atom_entry,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # check we updated the metadata part
    requests_meta = DepositRequest.objects.filter(deposit=deposit, type="metadata")
    assert len(requests_meta) == 1
    request_meta1 = requests_meta[0]
    raw_metadata1 = request_meta1.raw_metadata
    assert raw_metadata1 == data_atom_entry
    assert raw_metadata0 != raw_metadata1
    assert request_meta0 != request_meta1

    # and the archive part
    requests_archive1 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive1) == 1
    assert set(requests_archive0) != set(requests_archive1)
