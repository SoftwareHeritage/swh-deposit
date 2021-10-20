# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from io import BytesIO

from django.urls import reverse_lazy as reverse
from rest_framework import status
import xmltodict

from swh.deposit.config import (
    COL_IRI,
    DEPOSIT_STATUS_LOAD_FAILURE,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    DEPOSIT_STATUS_PARTIAL,
    SE_IRI,
)
from swh.deposit.models import Deposit
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import post_atom

from ..conftest import internal_create_deposit


def test_act_on_deposit_rejected_is_not_permitted(
    authenticated_client, deposit_collection, rejected_deposit, atom_dataset
):
    deposit = rejected_deposit

    response = post_atom(
        authenticated_client,
        reverse(SE_IRI, args=[deposit.collection.name, deposit.id]),
        data=atom_dataset["entry-data1"],
        HTTP_SLUG=deposit.external_id,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        xmltodict.parse(response.content)["sword:error"]["summary"]
        == f"You can only act on deposit with status '{DEPOSIT_STATUS_PARTIAL}'"
    )


def test_add_deposit_when_partial_makes_new_deposit(
    authenticated_client,
    deposit_collection,
    partial_deposit,
    atom_dataset,
    deposit_user,
):
    """Posting deposit on collection when previous is partial makes new deposit

    """
    deposit = partial_deposit
    assert deposit.status == DEPOSIT_STATUS_PARTIAL
    origin_url = deposit_user.provider_url + deposit.external_id

    # adding a new deposit with the same external id
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data0"] % origin_url,
        HTTP_SLUG=deposit.external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED, response.content.decode()
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    assert deposit_id != deposit.id  # new deposit

    new_deposit = Deposit.objects.get(pk=deposit_id)
    assert new_deposit != deposit
    assert new_deposit.parent is None
    assert new_deposit.origin_url == origin_url


def test_add_deposit_when_failed_makes_new_deposit_with_no_parent(
    authenticated_client, deposit_collection, failed_deposit, atom_dataset, deposit_user
):
    """Posting deposit on collection when deposit done makes new deposit with
    parent

    """
    deposit = failed_deposit
    assert deposit.status == DEPOSIT_STATUS_LOAD_FAILURE
    origin_url = deposit_user.provider_url + deposit.external_id

    # adding a new deposit with the same external id as a completed deposit
    # creates the parenting chain
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data0"] % origin_url,
        HTTP_SLUG=deposit.external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    assert deposit_id != deposit.id

    new_deposit = Deposit.objects.get(pk=deposit_id)
    assert new_deposit != deposit
    assert new_deposit.parent is None
    assert new_deposit.origin_url == origin_url


def test_add_deposit_when_done_makes_new_deposit_with_parent_old_one(
    authenticated_client,
    deposit_collection,
    completed_deposit,
    atom_dataset,
    deposit_user,
):
    """Posting deposit on collection when deposit done makes new deposit with
    parent

    """
    # given multiple deposit already loaded
    deposit = completed_deposit
    assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS
    origin_url = deposit_user.provider_url + deposit.external_id

    # adding a new deposit with the same external id as a completed deposit
    # creates the parenting chain
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data0"] % origin_url,
        HTTP_SLUG=deposit.external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    assert deposit_id != deposit.id

    new_deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == new_deposit.collection
    assert deposit.origin_url == origin_url

    assert new_deposit != deposit
    assert new_deposit.parent == deposit
    assert new_deposit.origin_url == origin_url


def test_add_deposit_with_external_identifier(
    authenticated_client,
    deposit_collection,
    completed_deposit,
    atom_dataset,
    deposit_user,
):
    """Even though <external_identifier> is deprecated, it should still be
    allowed when it matches the slug, so that we don't break existing clients

    """
    # given multiple deposit already loaded
    deposit = completed_deposit
    assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS
    origin_url = deposit_user.provider_url + deposit.external_id

    # adding a new deposit with the same external id as a completed deposit
    # creates the parenting chain
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["error-with-external-identifier"] % deposit.external_id,
        HTTP_SLUG=deposit.external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    assert deposit_id != deposit.id

    new_deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == new_deposit.collection
    assert deposit.origin_url == origin_url

    assert new_deposit != deposit
    assert new_deposit.parent == deposit
    assert new_deposit.origin_url == origin_url


def test_add_deposit_external_id_conflict_no_parent(
    authenticated_client,
    deposit_collection,
    deposit_another_collection,
    atom_dataset,
    deposit_user,
    deposit_another_user,
):
    """Posting a deposit with an external_id conflicting with an external_id
    of a different client does not create a parent relationship

    """
    external_id = "foobar"
    origin_url = deposit_user.provider_url + external_id

    # create a deposit for that other user, with the same slug
    other_deposit = internal_create_deposit(
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
        HTTP_SLUG=external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    assert other_deposit.id != deposit_id

    new_deposit = Deposit.objects.get(pk=deposit_id)

    assert new_deposit.parent is None
    assert new_deposit.origin_url == origin_url


def test_add_deposit_external_id_conflict_with_parent(
    authenticated_client,
    deposit_collection,
    deposit_another_collection,
    completed_deposit,
    atom_dataset,
    deposit_user,
    deposit_another_user,
):
    """Posting a deposit with an external_id conflicting with an external_id
    of a different client creates a parent relationship with the deposit
    of the right client instead of the last matching deposit

    This test does not have an equivalent for origin url conflicts, as these
    can not happen (assuming clients do not have provider_url overlaps)
    """
    # given multiple deposit already loaded
    deposit = completed_deposit
    assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS
    origin_url = deposit_user.provider_url + deposit.external_id

    # create a deposit for that other user, with the same slug
    other_deposit = internal_create_deposit(
        deposit_another_user,
        deposit_another_collection,
        deposit.external_id,
        DEPOSIT_STATUS_LOAD_SUCCESS,
    )

    # adding a new deposit with the same external id as a completed deposit
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data0"] % origin_url,
        HTTP_SLUG=deposit.external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    assert deposit_id != deposit.id
    assert other_deposit.id != deposit.id

    new_deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == new_deposit.collection
    assert deposit.external_id == new_deposit.external_id

    assert new_deposit != deposit
    assert new_deposit.parent == deposit
    assert new_deposit.origin_url == origin_url
