# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
from django.urls import reverse
from rest_framework import status
from typing import Dict, Mapping

from swh.deposit.config import (
    EDIT_SE_IRI,
    EM_IRI,
    ARCHIVE_KEY,
    METADATA_KEY,
    DEPOSIT_STATUS_DEPOSITED,
)

from swh.deposit.models import Deposit, DepositRequest


def count_deposit_request_types(deposit_requests) -> Mapping[str, int]:
    deposit_request_types = defaultdict(int)  # type: Dict[str, int]
    for dr in deposit_requests:
        deposit_request_types[dr.type] += 1
    return deposit_request_types


def test_delete_archive_on_partial_deposit_works(
    authenticated_client, partial_deposit_with_metadata, deposit_collection
):
    """Removing partial deposit's archive should return a 204 response

    """
    deposit_id = partial_deposit_with_metadata.id
    deposit = Deposit.objects.get(pk=deposit_id)
    deposit_requests = DepositRequest.objects.filter(deposit=deposit)

    # deposit request type: 'archive', 1 'metadata'
    deposit_request_types = count_deposit_request_types(deposit_requests)
    assert deposit_request_types == {ARCHIVE_KEY: 1, METADATA_KEY: 1}

    # when
    update_uri = reverse(EM_IRI, args=[deposit_collection.name, deposit_id])
    response = authenticated_client.delete(update_uri)

    # then
    assert response.status_code == status.HTTP_204_NO_CONTENT

    deposit = Deposit.objects.get(pk=deposit_id)
    deposit_requests2 = DepositRequest.objects.filter(deposit=deposit)

    deposit_request_types = count_deposit_request_types(deposit_requests2)
    assert deposit_request_types == {METADATA_KEY: 1}


def test_delete_archive_on_undefined_deposit_fails(
    authenticated_client, deposit_collection, sample_archive
):
    """Delete undefined deposit returns a 404 response

    """
    # when
    update_uri = reverse(EM_IRI, args=[deposit_collection.name, 999])
    response = authenticated_client.delete(update_uri)
    # then
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_non_partial_deposit(
    authenticated_client, deposit_collection, deposited_deposit
):
    """Delete !partial status deposit should return a 400 response

    """
    deposit = deposited_deposit
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    # when
    update_uri = reverse(EM_IRI, args=[deposit_collection.name, deposit.id])
    response = authenticated_client.delete(update_uri)
    # then
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    deposit = Deposit.objects.get(pk=deposit.id)
    assert deposit is not None


def test_delete_partial_deposit(
    authenticated_client, deposit_collection, partial_deposit
):
    """Delete deposit should return a 204 response

    """
    # given
    deposit = partial_deposit

    # when
    url = reverse(EDIT_SE_IRI, args=[deposit_collection.name, deposit.id])
    response = authenticated_client.delete(url)
    # then
    assert response.status_code == status.HTTP_204_NO_CONTENT
    deposit_requests = list(DepositRequest.objects.filter(deposit=deposit))
    assert deposit_requests == []
    deposits = list(Deposit.objects.filter(pk=deposit.id))
    assert deposits == []


def test_delete_on_edit_se_iri_cannot_delete_non_partial_deposit(
    authenticated_client, deposit_collection, complete_deposit
):
    """Delete !partial deposit should return a 400 response

    """
    # given
    deposit = complete_deposit

    # when
    url = reverse(EDIT_SE_IRI, args=[deposit_collection.name, deposit.id])
    response = authenticated_client.delete(url)
    # then
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    deposit = Deposit.objects.get(pk=deposit.id)
    assert deposit is not None
