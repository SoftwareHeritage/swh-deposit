# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.urls import reverse_lazy as reverse
from rest_framework import status

from swh.deposit.api.converters import convert_status_detail
from swh.deposit.config import (
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    DEPOSIT_STATUS_PARTIAL,
    PRIVATE_LIST_DEPOSITS,
)
from swh.deposit.models import DepositClient
from swh.deposit.tests.conftest import internal_create_deposit

STATUS_DETAIL = {
    "url": {
        "summary": "At least one compatible url field. Failed",
        "fields": ["testurl"],
    },
    "metadata": [{"summary": "Mandatory fields missing", "fields": ["9", 10, 1.212],},],
    "archive": [
        {"summary": "Invalid archive", "fields": ["3"],},
        {"summary": "Unsupported archive", "fields": [2],},
    ],
}


def test_deposit_list(partial_deposit, deposited_deposit, authenticated_client):
    """Deposit list api should return all deposits in a paginated way

    """
    partial_deposit.status_detail = STATUS_DETAIL
    partial_deposit.save()

    deposit_id = partial_deposit.id
    deposit_id2 = deposited_deposit.id

    main_url = reverse(PRIVATE_LIST_DEPOSITS)
    url = "%s?page_size=1" % main_url
    response = authenticated_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["count"] == 2  # total result of 2 deposits if consuming all results
    expected_next = f"{main_url}?page=2&page_size=1"
    assert data["next"].endswith(expected_next) is True
    assert data["previous"] is None
    assert len(data["results"]) == 1  # page of size 1
    deposit = data["results"][0]
    assert deposit["id"] == deposit_id
    assert deposit["status"] == DEPOSIT_STATUS_PARTIAL
    expected_status_detail = convert_status_detail(STATUS_DETAIL)
    assert deposit["status_detail"] == expected_status_detail

    # then 2nd page
    response2 = authenticated_client.get(expected_next)

    assert response2.status_code == status.HTTP_200_OK
    data2 = response2.json()

    assert data["count"] == 2  # total result of 2 deposits if consuming all results
    assert data2["next"] is None

    expected_previous = f"{main_url}?page_size=1"
    assert data2["previous"].endswith(expected_previous) is True
    assert len(data2["results"]) == 1  # page of size 1

    deposit2 = data2["results"][0]
    assert deposit2["id"] == deposit_id2
    assert deposit2["status"] == DEPOSIT_STATUS_DEPOSITED


def test_deposit_list_exclude(partial_deposit, deposited_deposit, authenticated_client):
    """Exclusion pattern on external_id should be respected

    """
    partial_deposit.status_detail = STATUS_DETAIL
    partial_deposit.save()

    main_url = reverse(PRIVATE_LIST_DEPOSITS)

    # Testing exclusion pattern
    exclude_pattern = "external-id"
    assert partial_deposit.external_id.startswith(exclude_pattern)
    assert deposited_deposit.external_id.startswith(exclude_pattern)
    url = f"{main_url}?page_size=1&exclude=external-id"
    response = authenticated_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["count"] == 0

    url = "%s?page_size=1&exclude=dummy" % main_url  # that won't exclude anything
    response = authenticated_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["count"] == 2


def test_deposit_list_for_username(
    authenticated_client,
    deposit_another_collection,
    completed_deposit,
    deposit_user,
    deposit_another_user,
):

    # create a new deposit with a user different from deposit_user,
    # the one that created completed_deposit
    internal_create_deposit(
        client=deposit_another_user,
        collection=deposit_another_collection,
        external_id="external-id-bar",
        status=DEPOSIT_STATUS_LOAD_SUCCESS,
    )

    for user in (deposit_user, deposit_another_user):
        # check deposit filtering by username
        url = f"{reverse(PRIVATE_LIST_DEPOSITS)}?username={user.username}"
        json_response = authenticated_client.get(url).json()

        assert len(json_response["results"]) == 1

        deposit_client = DepositClient.objects.all().get(
            id=json_response["results"][0]["client"]
        )
        assert deposit_client.username == user.username
