# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from io import BytesIO

from django.urls import reverse_lazy as reverse
from requests.utils import parse_header_links
from rest_framework import status

from swh.deposit.config import COL_IRI, DEPOSIT_STATUS_DEPOSITED, DEPOSIT_STATUS_PARTIAL
from swh.deposit.models import DepositCollection
from swh.deposit.parsers import parse_xml


def test_deposit_collection_list_is_auth_protected(anonymous_client):
    """Deposit list should require authentication

    """
    url = reverse(COL_IRI, args=("test",))
    response = anonymous_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert b"protected by basic authentication" in response.content


def test_deposit_collection_list_collection_access_restricted_to_user_coll(
    deposit_another_collection, deposit_user, authenticated_client
):
    """Deposit list api should restrict access to user's collection

    """
    collection_id = authenticated_client.deposit_client.collections[0]
    coll = DepositCollection.objects.get(pk=collection_id)
    # authenticated_client has access to the "coll" collection
    coll2 = deposit_another_collection
    assert coll.name != coll2.name
    # but does not have access to that coll2 collection
    url = reverse(COL_IRI, args=(coll2.name,))
    response = authenticated_client.get(url)
    # so it gets rejected access to the listing of that coll2 collection
    assert response.status_code == status.HTTP_403_FORBIDDEN
    msg = f"{deposit_user.username} cannot access collection {coll2.name}"
    assert msg in response.content.decode("utf-8")


def test_deposit_collection_list_nominal(
    partial_deposit, deposited_deposit, authenticated_client
):
    """Deposit list api should return the user deposits in a paginated way

    """
    client_id = authenticated_client.deposit_client.id
    assert partial_deposit.client.id == client_id
    assert deposited_deposit.client.id == client_id
    # Both deposit were deposited by the authenticated client
    # so requesting the listing of the deposits, both should be listed

    deposit_id = str(partial_deposit.id)
    deposit_id2 = str(deposited_deposit.id)
    coll = partial_deposit.collection
    # requesting the listing of the deposit for the user's collection
    url = reverse(COL_IRI, args=(coll.name,))
    response = authenticated_client.get(f"{url}?page_size=1")
    assert response.status_code == status.HTTP_200_OK

    data = parse_xml(BytesIO(response.content))["atom:feed"]
    assert (
        data["swh:count"] == "2"
    )  # total result of 2 deposits if consuming all results
    header_link = parse_header_links(response["Link"])
    assert len(header_link) == 1  # only 1 next link
    expected_next = f"{url}?page=2&page_size=1"
    assert header_link[0]["url"].endswith(expected_next)
    assert header_link[0]["rel"] == "next"

    # only one deposit in the response
    deposit = data["atom:entry"]  # dict as only 1 value (a-la js)
    assert isinstance(deposit, dict)
    assert deposit["swh:id"] == deposit_id
    assert deposit["swh:status"] == DEPOSIT_STATUS_PARTIAL

    # then 2nd page
    response2 = authenticated_client.get(expected_next)

    assert response2.status_code == status.HTTP_200_OK
    data2 = parse_xml(BytesIO(response2.content))["atom:feed"]
    assert data2["swh:count"] == "2"  # still total of 2 deposits across all results

    expected_previous = f"{url}?page_size=1"
    header_link2 = parse_header_links(response2["Link"])
    assert len(header_link2) == 1  # only 1 previous link
    assert header_link2[0]["url"].endswith(expected_previous)
    assert header_link2[0]["rel"] == "previous"

    # only 1 deposit in the response
    deposit2 = data2["atom:entry"]  # dict as only 1 value (a-la js)
    assert isinstance(deposit2, dict)
    assert deposit2["swh:id"] == deposit_id2
    assert deposit2["swh:status"] == DEPOSIT_STATUS_DEPOSITED

    # Retrieve every deposit in one query (no page_size parameter)
    response3 = authenticated_client.get(url)
    assert response3.status_code == status.HTTP_200_OK
    data3 = parse_xml(BytesIO(response3.content))["atom:feed"]
    assert data3["swh:count"] == "2"  # total result of 2 deposits across all results
    deposits3 = data3["atom:entry"]  # list here
    assert isinstance(deposits3, list)
    assert len(deposits3) == 2
    header_link3 = parse_header_links(response3["Link"])
    assert header_link3 == []  # no pagination as all results received in one round
    assert deposit in deposits3
    assert deposit2 in deposits3
