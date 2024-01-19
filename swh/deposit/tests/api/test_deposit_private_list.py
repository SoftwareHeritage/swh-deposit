# Copyright (C) 2017-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.http import QueryDict
from django.test import override_settings
from django.urls import reverse_lazy as reverse
import pytest
from rest_framework import status

from swh.deposit.api.converters import convert_status_detail
from swh.deposit.config import (
    DEPOSIT_STATUS_LOAD_SUCCESS,
    PRIVATE_LIST_DEPOSITS,
    PRIVATE_LIST_DEPOSITS_DATATABLES,
)
from swh.deposit.models import DEPOSIT_CODE, DEPOSIT_METADATA_ONLY, DepositClient
from swh.deposit.tests.conftest import internal_create_deposit

STATUS_DETAIL = {
    "url": {
        "summary": "At least one compatible url field. Failed",
        "fields": ["testurl"],
    },
    "metadata": [
        {
            "summary": "Mandatory fields missing",
            "fields": ["9", 10, 1.212],
        },
    ],
    "archive": [
        {
            "summary": "Invalid archive",
            "fields": ["3"],
        },
        {
            "summary": "Unsupported archive",
            "fields": [2],
        },
    ],
}


@pytest.fixture()
def partial_deposit_only_metadata(partial_deposit_only_metadata):
    partial_deposit_only_metadata.type = DEPOSIT_METADATA_ONLY
    partial_deposit_only_metadata.save()
    return partial_deposit_only_metadata


def test_deposit_list(
    partial_deposit_with_metadata,
    partial_deposit_only_metadata,
    partial_deposit,
    authenticated_client,
):
    """Deposit list api should return all deposits in a paginated way"""
    partial_deposit_with_metadata.status_detail = STATUS_DETAIL
    partial_deposit_with_metadata.save()
    deposit1 = partial_deposit_with_metadata
    deposit2 = partial_deposit_only_metadata
    deposit3 = partial_deposit

    main_url = reverse(PRIVATE_LIST_DEPOSITS)
    url = f"{main_url}?page_size=1"
    response = authenticated_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    data_p1 = response.json()
    assert data_p1["count"] == 3  # total nb of deposits
    expected_next_p1 = f"{main_url}?page=2&page_size=1"
    assert data_p1["next"].endswith(expected_next_p1) is True
    assert data_p1["previous"] is None
    assert len(data_p1["results"]) == 1  # page of size 1
    deposit_d = data_p1["results"][0]
    assert deposit_d["id"] == deposit1.id
    assert deposit_d["status"] == deposit1.status
    expected_status_detail = convert_status_detail(STATUS_DETAIL)
    assert deposit_d["status_detail"] == expected_status_detail
    assert deposit_d["raw_metadata"] is not None
    assert deposit_d["type"] == DEPOSIT_CODE
    assert (
        deposit_d["raw_metadata"]
        == deposit1.depositrequest_set.filter(type="metadata")[0].raw_metadata
    )

    # then 2nd page
    response2 = authenticated_client.get(data_p1["next"])

    assert response2.status_code == status.HTTP_200_OK
    data_p2 = response2.json()

    assert data_p2["count"] == 3  # total nb of deposits
    expected_next_p2 = f"{main_url}?page=3&page_size=1"
    assert data_p2["next"].endswith(expected_next_p2)
    assert data_p2["previous"].endswith(url)
    assert len(data_p2["results"]) == 1  # page of size 1

    deposit2_d = data_p2["results"][0]
    assert deposit2_d["id"] == deposit2.id
    assert deposit2_d["status"] == deposit2.status
    assert deposit2_d["raw_metadata"] is not None
    assert deposit2_d["type"] == DEPOSIT_METADATA_ONLY
    assert (
        deposit2_d["raw_metadata"]
        == deposit2.depositrequest_set.filter(type="metadata")[0].raw_metadata
    )

    # then 3rd (and last) page
    response3 = authenticated_client.get(data_p2["next"])

    assert response3.status_code == status.HTTP_200_OK
    data_p3 = response3.json()

    assert data_p3["count"] == 3  # total nb of deposits
    assert data_p3["next"] is None, "No more page beyond that point"

    assert data_p3["previous"] == data_p1["next"]
    assert len(data_p3["results"]) == 1  # page of size 1

    deposit3_d = data_p3["results"][0]
    assert deposit3_d["id"] == deposit3.id
    assert deposit3_d["status"] == deposit3.status
    assert deposit3_d["type"] == DEPOSIT_CODE
    assert not deposit3.depositrequest_set.filter(
        type="metadata"
    ), "No metadata type request for that deposit"
    # hence no raw metadata set for that deposit
    assert deposit3_d["raw_metadata"] is None, "no raw metadata for that deposit"


def test_deposit_list_exclude(partial_deposit, deposited_deposit, authenticated_client):
    """Exclusion pattern on external_id should be respected"""
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


@pytest.fixture()
def deposits(
    partial_deposit_with_metadata,
    partial_deposit_only_metadata,
    partial_deposit,
    completed_deposit,
    complete_deposit,
):
    # to cover code extracting deposit provenance from swhid_context
    complete_deposit.origin_url = None
    complete_deposit.save()

    return [
        partial_deposit_with_metadata,
        partial_deposit_only_metadata,
        partial_deposit,
        completed_deposit,
        complete_deposit,
    ]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_deposit_list_datatables_empty_query(
    deposits,
    authenticated_client,
):
    url = reverse(PRIVATE_LIST_DEPOSITS_DATATABLES)
    deposits_dt_data = authenticated_client.get(url).json()
    assert deposits_dt_data["draw"] == 1
    assert deposits_dt_data["recordsTotal"] == len(deposits)
    assert deposits_dt_data["recordsFiltered"] == len(deposits)
    assert len(deposits_dt_data["data"]) == len(deposits)
    # by default, deposits are sorted by decreasing ids
    assert [d["id"] for d in deposits_dt_data["data"]] == list(
        reversed(sorted([d.id for d in deposits]))
    )


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_deposit_list_datatables_pagination(
    deposits,
    authenticated_client,
):
    deposits_data = []
    for i in range(len(deposits)):
        query_params = QueryDict(mutable=True)
        query_params.update(
            {
                "draw": i + 1,
                "length": 1,
                "start": i,
            }
        )
        url = reverse(PRIVATE_LIST_DEPOSITS_DATATABLES) + "?" + query_params.urlencode()
        deposits_dt_data = authenticated_client.get(url).json()
        deposits_data += deposits_dt_data["data"]

    assert [d["id"] for d in deposits_data] == list(
        reversed(sorted([d.id for d in deposits]))
    )


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("sort_direction", ["asc", "desc"])
def test_deposit_list_datatables_ordering(
    deposits,
    authenticated_client,
    sort_direction,
):
    deposits_date_sorted = list(sorted(deposits, key=lambda d: d.reception_date))

    if sort_direction == "desc":
        deposits_date_sorted = list(reversed(deposits_date_sorted))

    query_params = QueryDict(mutable=True)
    query_params.update(
        {
            "draw": 1,
            "length": 10,
            "start": 0,
            "order[0][column]": 4,
            "order[0][dir]": sort_direction,
            "columns[4][name]": "reception_date",
        }
    )
    url = reverse(PRIVATE_LIST_DEPOSITS_DATATABLES) + "?" + query_params.urlencode()

    deposits_dt_data = authenticated_client.get(url).json()

    reception_dates = [d["reception_date"] for d in deposits_dt_data["data"]]
    expected_dates = [
        d.reception_date.isoformat().replace("+00:00", "Z")
        for d in deposits_date_sorted
    ]

    assert reception_dates == expected_dates


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_deposit_list_datatables_search(
    deposits,
    authenticated_client,
):
    query_params = QueryDict(mutable=True)
    query_params.update(
        {
            "draw": 1,
            "length": 10,
            "start": 0,
            "search[value]": DEPOSIT_STATUS_LOAD_SUCCESS,
        }
    )
    url = reverse(PRIVATE_LIST_DEPOSITS_DATATABLES) + "?" + query_params.urlencode()

    deposits_dt_data = authenticated_client.get(url).json()

    deposits_load_success = [
        d for d in deposits if d.status == DEPOSIT_STATUS_LOAD_SUCCESS
    ]

    deposits_load_success = list(
        reversed(sorted(deposits_load_success, key=lambda d: d.id))
    )

    assert deposits_load_success

    assert [d.id for d in deposits_load_success] == [
        d["id"] for d in deposits_dt_data["data"]
    ]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_deposit_list_datatables_exclude_pattern(
    deposits,
    authenticated_client,
):
    query_params = QueryDict(mutable=True)
    query_params.update(
        {
            "draw": 1,
            "length": 10,
            "start": 0,
            "excludePattern": DEPOSIT_STATUS_LOAD_SUCCESS,
        }
    )
    url = reverse(PRIVATE_LIST_DEPOSITS_DATATABLES) + "?" + query_params.urlencode()

    deposits_dt_data = authenticated_client.get(url).json()

    deposits_load_not_success = [
        d for d in deposits if d.status != DEPOSIT_STATUS_LOAD_SUCCESS
    ]

    deposits_load_not_success = list(
        reversed(sorted(deposits_load_not_success, key=lambda d: d.id))
    )

    assert deposits_load_not_success

    assert [d.id for d in deposits_load_not_success] == [
        d["id"] for d in deposits_dt_data["data"]
    ]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_deposit_list_datatables_username(
    completed_deposit,
    deposit_user,
    deposit_another_user,
    deposit_another_collection,
    authenticated_client,
):
    # create a new deposit with a user different from deposit_user,
    # the one that created completed_deposit
    completed_deposit_another_user = internal_create_deposit(
        client=deposit_another_user,
        collection=deposit_another_collection,
        external_id="external-id-bar",
        status=DEPOSIT_STATUS_LOAD_SUCCESS,
    )

    for user, deposit in (
        (deposit_user, completed_deposit),
        (deposit_another_user, completed_deposit_another_user),
    ):
        query_params = QueryDict(mutable=True)
        query_params["username"] = user.username
        url = reverse(PRIVATE_LIST_DEPOSITS_DATATABLES) + "?" + query_params.urlencode()

        deposits_dt_data = authenticated_client.get(url).json()

        assert len(deposits_dt_data["data"]) == 1
        assert deposits_dt_data["data"][0]["id"] == deposit.id


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@override_settings(DEBUG=True)
def test_deposit_list_datatables_error(
    deposits,
    authenticated_client,
    mocker,
):
    parse_swh_metadata_provenance = mocker.patch(
        "swh.deposit.api.private.deposit_list.parse_swh_metadata_provenance"
    )
    error_message = "Error when parsing metadata"
    parse_swh_metadata_provenance.side_effect = Exception(error_message)
    url = reverse(PRIVATE_LIST_DEPOSITS_DATATABLES)
    deposits_dt_data = authenticated_client.get(url).json()
    assert "error" in deposits_dt_data
    assert error_message in deposits_dt_data["error"]
