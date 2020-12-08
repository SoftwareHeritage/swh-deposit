# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib
from io import BytesIO

from django.urls import reverse
from rest_framework import status

from swh.deposit.config import (
    COL_IRI,
    DEPOSIT_STATUS_LOAD_FAILURE,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    DEPOSIT_STATUS_PARTIAL,
    DEPOSIT_STATUS_REJECTED,
    SE_IRI,
)
from swh.deposit.models import Deposit
from swh.deposit.parsers import parse_xml

from ..conftest import create_deposit


def test_deposit_post_will_fail_with_401(client):
    """Without authentication, endpoint refuses access with 401 response

    """
    url = reverse(COL_IRI, args=["hal"])
    response = client.post(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_access_to_another_user_collection_is_forbidden(
    authenticated_client, deposit_another_collection, deposit_user
):
    """Access to another user collection should return a 403

    """
    coll2 = deposit_another_collection
    url = reverse(COL_IRI, args=[coll2.name])
    response = authenticated_client.post(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    msg = "Client %s cannot access collection %s" % (deposit_user.username, coll2.name,)
    assert msg in response.content.decode("utf-8")


def test_delete_on_col_iri_not_supported(authenticated_client, deposit_collection):
    """Delete on col iri should return a 405 response

    """
    url = reverse(COL_IRI, args=[deposit_collection.name])
    response = authenticated_client.delete(url)
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert "DELETE method is not supported on this endpoint" in response.content.decode(
        "utf-8"
    )


def create_deposit_with_rejection_status(authenticated_client, deposit_collection):
    url = reverse(COL_IRI, args=[deposit_collection.name])

    data = b"some data which is clearly not a zip file"
    md5sum = hashlib.md5(data).hexdigest()
    external_id = "some-external-id-1"

    # when
    response = authenticated_client.post(
        url,
        content_type="application/zip",  # as zip
        data=data,
        # + headers
        CONTENT_LENGTH=len(data),
        # other headers needs HTTP_ prefix to be taken into account
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=md5sum,
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    actual_state = response_content["deposit_status"]
    assert actual_state == DEPOSIT_STATUS_REJECTED


def test_act_on_deposit_rejected_is_not_permitted(
    authenticated_client, deposit_collection, rejected_deposit, atom_dataset
):
    deposit = rejected_deposit

    response = authenticated_client.post(
        reverse(SE_IRI, args=[deposit.collection.name, deposit.id]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data1"],
        HTTP_SLUG=deposit.external_id,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    msg = "You can only act on deposit with status &#39;%s&#39;" % (
        DEPOSIT_STATUS_PARTIAL,
    )
    assert msg in response.content.decode("utf-8")


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
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
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
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
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
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
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


def test_add_deposit_with_add_to_origin(
    authenticated_client,
    deposit_collection,
    completed_deposit,
    atom_dataset,
    deposit_user,
):
    """Posting deposit with <swh:add_to_origin> creates a new deposit with parent

    """
    # given multiple deposit already loaded
    deposit = completed_deposit
    assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS
    origin_url = deposit_user.provider_url + deposit.external_id

    # adding a new deposit with the same external id as a completed deposit
    # creates the parenting chain
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-with-add-to-origin"] % origin_url,
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


def test_add_deposit_external_id_conflict_no_parent(
    authenticated_client,
    another_authenticated_client,
    deposit_collection,
    deposit_another_collection,
    atom_dataset,
    sample_archive,
    deposit_user,
):
    """Posting a deposit with an external_id conflicting with an external_id
    of a different client does not create a parent relationship

    """
    external_id = "foobar"
    origin_url = deposit_user.provider_url + external_id

    # create a deposit for that other user, with the same slug
    other_deposit = create_deposit(
        another_authenticated_client,
        deposit_another_collection.name,
        sample_archive,
        external_id,
        DEPOSIT_STATUS_LOAD_SUCCESS,
    )

    # adding a new deposit with the same external id as a completed deposit
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data0"] % origin_url,
        HTTP_SLUG=external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    assert other_deposit.id != deposit_id

    new_deposit = Deposit.objects.get(pk=deposit_id)

    assert new_deposit.parent is None


def test_add_deposit_external_id_conflict_with_parent(
    authenticated_client,
    another_authenticated_client,
    deposit_collection,
    deposit_another_collection,
    completed_deposit,
    atom_dataset,
    sample_archive,
    deposit_user,
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
    other_deposit = create_deposit(
        another_authenticated_client,
        deposit_another_collection.name,
        sample_archive,
        deposit.external_id,
        DEPOSIT_STATUS_LOAD_SUCCESS,
    )

    # adding a new deposit with the same external id as a completed deposit
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
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


def test_add_deposit_add_to_origin_conflict(
    authenticated_client,
    another_authenticated_client,
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
    create_deposit(
        another_authenticated_client,
        deposit_another_collection.name,
        sample_archive,
        external_id,
        DEPOSIT_STATUS_LOAD_SUCCESS,
    )

    # adding a new deposit with the same external id as a completed deposit
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data0"] % origin_url,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert b"must start with" in response.content


def test_add_deposit_add_to_wrong_origin(
    authenticated_client, deposit_collection, atom_dataset, sample_archive,
):
    """Posting a deposit with an <swh:add_to_origin> referencing an origin
    not starting with the provider_url raises an error

    """
    origin_url = "http://example.org/foo"

    # adding a new deposit with the same external id as a completed deposit
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data0"] % origin_url,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert b"must start with" in response.content
