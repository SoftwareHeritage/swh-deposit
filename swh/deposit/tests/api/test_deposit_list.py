# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.urls import reverse
from rest_framework import status

from swh.deposit.api.converters import convert_status_detail
from swh.deposit.config import (
    DEPOSIT_STATUS_PARTIAL,
    PRIVATE_LIST_DEPOSITS,
    DEPOSIT_STATUS_DEPOSITED,
)

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

    # NOTE: does not work as documented
    # https://docs.djangoproject.com/en/1.11/ref/urlresolvers/#django.core.urlresolvers.reverse  # noqa
    # url = reverse(PRIVATE_LIST_DEPOSITS, kwargs={'page_size': 1})
    main_url = reverse(PRIVATE_LIST_DEPOSITS)
    url = "%s?page_size=1" % main_url
    response = authenticated_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["count"] == 2  # 2 deposits
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

    assert data2["count"] == 2  # still 2 deposits
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
