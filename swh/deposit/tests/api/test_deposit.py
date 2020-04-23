# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib

from django.urls import reverse
from io import BytesIO
from rest_framework import status

from swh.deposit.config import (
    COL_IRI,
    EDIT_SE_IRI,
    DEPOSIT_STATUS_REJECTED,
    DEPOSIT_STATUS_PARTIAL,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    DEPOSIT_STATUS_LOAD_FAILURE,
)

from swh.deposit.models import Deposit
from swh.deposit.parsers import parse_xml


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
        reverse(EDIT_SE_IRI, args=[deposit.collection.name, deposit.id]),
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
    authenticated_client, deposit_collection, partial_deposit, atom_dataset
):
    """Posting deposit on collection when previous is partial makes new deposit

    """
    deposit = partial_deposit
    assert deposit.status == DEPOSIT_STATUS_PARTIAL

    # adding a new deposit with the same external id
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data0"] % deposit.external_id,
        HTTP_SLUG=deposit.external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["deposit_id"]

    assert deposit_id != deposit.id  # new deposit

    new_deposit = Deposit.objects.get(pk=deposit_id)
    assert new_deposit != deposit
    assert new_deposit.parent is None


def test_add_deposit_when_failed_makes_new_deposit_with_no_parent(
    authenticated_client, deposit_collection, failed_deposit, atom_dataset
):
    """Posting deposit on collection when deposit done makes new deposit with
    parent

    """
    deposit = failed_deposit
    assert deposit.status == DEPOSIT_STATUS_LOAD_FAILURE

    # adding a new deposit with the same external id as a completed deposit
    # creates the parenting chain
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data0"] % deposit.external_id,
        HTTP_SLUG=deposit.external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["deposit_id"]

    assert deposit_id != deposit.id

    new_deposit = Deposit.objects.get(pk=deposit_id)
    assert new_deposit != deposit
    assert new_deposit.parent is None


def test_add_deposit_when_done_makes_new_deposit_with_parent_old_one(
    authenticated_client, deposit_collection, completed_deposit, atom_dataset
):
    """Posting deposit on collection when deposit done makes new deposit with
    parent

    """
    # given multiple deposit already loaded
    deposit = completed_deposit
    assert deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS

    # adding a new deposit with the same external id as a completed deposit
    # creates the parenting chain
    response = authenticated_client.post(
        reverse(COL_IRI, args=[deposit_collection.name]),
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data0"] % deposit.external_id,
        HTTP_SLUG=deposit.external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["deposit_id"]

    assert deposit_id != deposit.id

    new_deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == new_deposit.collection
    assert deposit.external_id == new_deposit.external_id

    assert new_deposit != deposit
    assert new_deposit.parent == deposit
