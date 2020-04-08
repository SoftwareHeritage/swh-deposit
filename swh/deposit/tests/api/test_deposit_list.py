# Copyright (C) 2017-2019  The Software Heritage developers
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


def test_deposit_list(partial_deposit, deposited_deposit, authenticated_client):
    """Deposit list api should return the deposits

    """
    status_detail = {
        "url": {
            "summary": "At least one compatible url field. Failed",
            "fields": ["testurl"],
        },
        "metadata": [
            {"summary": "Mandatory fields missing", "fields": ["9", 10, 1.212],},
        ],
        "archive": [
            {"summary": "Invalid archive", "fields": ["3"],},
            {"summary": "Unsupported archive", "fields": [2],},
        ],
    }
    partial_deposit.status_detail = status_detail
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
    expected_next = "%s?page=2&page_size=1" % main_url
    assert data["next"].endswith(expected_next) is True
    assert data["previous"] is None
    assert len(data["results"]) == 1  # page of size 1
    deposit = data["results"][0]
    assert deposit["id"] == deposit_id
    assert deposit["status"] == DEPOSIT_STATUS_PARTIAL
    expected_status_detail = convert_status_detail(status_detail)
    assert deposit["status_detail"] == expected_status_detail

    # then 2nd page
    response2 = authenticated_client.get(expected_next)

    assert response2.status_code == status.HTTP_200_OK
    data2 = response2.json()

    assert data2["count"] == 2  # still 2 deposits
    assert data2["next"] is None

    expected_previous = "%s?page_size=1" % main_url
    assert data2["previous"].endswith(expected_previous) is True
    assert len(data2["results"]) == 1  # page of size 1

    deposit2 = data2["results"][0]
    assert deposit2["id"] == deposit_id2
    assert deposit2["status"] == DEPOSIT_STATUS_DEPOSITED
