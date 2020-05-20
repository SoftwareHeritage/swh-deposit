# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from django.urls import reverse
from io import BytesIO
from rest_framework import status

from swh.deposit.config import (
    STATE_IRI,
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_REJECTED,
)
from swh.deposit.models import DEPOSIT_STATUS_DETAIL, DEPOSIT_STATUS_LOAD_SUCCESS
from swh.deposit.parsers import parse_xml


def test_post_deposit_with_status_check(authenticated_client, deposited_deposit):
    """Successful but not loaded deposit should have a status 'deposited'

    """
    deposit = deposited_deposit
    status_url = reverse(STATE_IRI, args=[deposit.collection.name, deposit.id])

    # check status
    status_response = authenticated_client.get(status_url)

    assert status_response.status_code == status.HTTP_200_OK
    r = parse_xml(BytesIO(status_response.content))

    assert int(r["deposit_id"]) == deposit.id
    assert r["deposit_status"] == DEPOSIT_STATUS_DEPOSITED
    assert r["deposit_status_detail"] == DEPOSIT_STATUS_DETAIL[DEPOSIT_STATUS_DEPOSITED]
    assert r["deposit_external_id"] == deposit.external_id


def test_status_unknown_deposit(authenticated_client, deposit_collection):
    """Unknown deposit status should return 404 response

    """
    unknown_deposit_id = 999
    status_url = reverse(STATE_IRI, args=[deposit_collection.name, unknown_deposit_id])
    status_response = authenticated_client.get(status_url)
    assert status_response.status_code == status.HTTP_404_NOT_FOUND


def test_status_unknown_collection(authenticated_client, deposited_deposit):
    """Unknown collection status should return 404 response"""
    deposit = deposited_deposit
    unknown_collection = "something-unknown"
    status_url = reverse(STATE_IRI, args=[unknown_collection, deposit.id])
    status_response = authenticated_client.get(status_url)
    assert status_response.status_code == status.HTTP_404_NOT_FOUND


def test_status_deposit_rejected(authenticated_client, rejected_deposit):
    """Rejected deposit status should be 'rejected' with detailed summary

    """
    deposit = rejected_deposit
    # _status_detail = {'url': {'summary': 'Wrong url'}}

    url = reverse(STATE_IRI, args=[deposit.collection.name, deposit.id])

    # when
    status_response = authenticated_client.get(url)

    # then
    assert status_response.status_code == status.HTTP_200_OK
    r = parse_xml(BytesIO(status_response.content))
    assert int(r["deposit_id"]) == deposit.id
    assert r["deposit_status"] == DEPOSIT_STATUS_REJECTED
    assert r["deposit_status_detail"] == "Deposit failed the checks"
    if deposit.swh_id:
        assert r["deposit_swh_id"] == deposit.swh_id


def test_status_with_http_accept_header_should_not_break(
    authenticated_client, partial_deposit
):
    """Asking deposit status with Accept header should return 200

    """
    deposit = partial_deposit

    status_url = reverse(STATE_IRI, args=[deposit.collection.name, deposit.id])

    response = authenticated_client.get(status_url)
    assert response.status_code == status.HTTP_200_OK

    response = authenticated_client.get(
        status_url, HTTP_ACCEPT="text/html,application/xml;q=9,*/*,q=8"
    )
    assert response.status_code == status.HTTP_200_OK


def test_status_complete_deposit(authenticated_client, complete_deposit):
    """Successful and loaded deposit should be 'done' and have detailed swh ids

    """
    deposit = complete_deposit
    url = reverse(STATE_IRI, args=[deposit.collection.name, deposit.id])

    # when
    status_response = authenticated_client.get(url)

    # then
    assert status_response.status_code == status.HTTP_200_OK
    r = parse_xml(BytesIO(status_response.content))
    assert int(r["deposit_id"]) == deposit.id
    assert r["deposit_status"] == DEPOSIT_STATUS_LOAD_SUCCESS
    assert (
        r["deposit_status_detail"] == DEPOSIT_STATUS_DETAIL[DEPOSIT_STATUS_LOAD_SUCCESS]
    )
    assert deposit.swh_id is not None
    assert r["deposit_swh_id"] == deposit.swh_id
    assert deposit.swh_id_context is not None
    assert r["deposit_swh_id_context"] == deposit.swh_id_context
