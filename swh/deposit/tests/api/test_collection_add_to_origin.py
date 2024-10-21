# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.urls import reverse_lazy as reverse
from rest_framework import status

from swh.deposit.config import COL_IRI, DEPOSIT_STATUS_LOAD_SUCCESS
from swh.deposit.models import Deposit
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import post_atom
from swh.deposit.tests.conftest import internal_create_deposit
from swh.deposit.utils import NAMESPACES


def test_add_deposit_with_add_to_origin(
    authenticated_client,
    deposit_collection,
    completed_deposit,
    atom_dataset,
    deposit_user,
):
    """Posting deposit with <swh:add_to_origin> creates a new deposit with parent"""
    # given multiple deposit already loaded
    deposit = completed_deposit
    assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS
    origin_url = deposit_user.provider_url + deposit.external_id

    # adding a new deposit with the same external id as a completed deposit
    # creates the parenting chain
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data-with-add-to-origin"] % origin_url,
    )

    assert response.status_code == status.HTTP_201_CREATED, response.content.decode()
    response_content = parse_xml(response.content)
    deposit_id = int(response_content.findtext("swh:deposit_id", namespaces=NAMESPACES))

    assert deposit_id != deposit.id

    new_deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == new_deposit.collection
    assert deposit.origin_url == origin_url

    assert new_deposit != deposit
    assert new_deposit.parent == deposit
    assert new_deposit.origin_url == origin_url


def test_add_deposit_add_to_origin_conflict(
    authenticated_client,
    deposit_collection,
    deposit_another_collection,
    atom_dataset,
    sample_archive,
    deposit_user,
    deposit_another_user,
):
    """Posting a deposit with an <swh:add_to_origin> referencing an origin
    owned by a different client raises an error

    """
    external_id = "foobar"
    origin_url = deposit_another_user.provider_url + external_id

    # create a deposit for that other user, with the same slug
    internal_create_deposit(
        deposit_another_user,
        deposit_another_collection,
        external_id,
        DEPOSIT_STATUS_LOAD_SUCCESS,
    )

    # adding a new deposit with the same external id as a completed deposit
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data0"] % origin_url,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert b"must start with" in response.content


def test_add_deposit_add_to_wrong_origin(
    authenticated_client,
    deposit_collection,
    atom_dataset,
    sample_archive,
):
    """Posting a deposit with an <swh:add_to_origin> referencing an origin
    not starting with the provider_url raises an error

    """
    origin_url = "http://example.org/foo"

    # adding a new deposit with the same external id as a completed deposit
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data0"] % origin_url,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN, response.content.decode()
    assert b"must start with" in response.content


def test_post_deposit_atom_403_add_to_wrong_origin_url_prefix(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """Creating an origin for a prefix not owned by the client is forbidden"""
    origin_url = "http://example.org/foo"

    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data-with-add-to-origin"] % origin_url,
        HTTP_IN_PROGRESS="true",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "URL mismatch" in response.content.decode()


def test_add_deposit_with_add_to_origin_missing_parent(
    authenticated_client,
    deposit_collection,
    completed_deposit,
    atom_dataset,
    deposit_user,
):
    """Add to an unknown origin"""
    origin_url = deposit_user.provider_url + "unknown_origin"
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data-with-add-to-origin"] % origin_url,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND, response.content.decode()
    assert "if you want to create a new Deposit" in response.content.decode()
