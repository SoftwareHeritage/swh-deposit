# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Tests the handling of the binary content when doing a POST Col-IRI."""

from io import BytesIO
import uuid

from django.urls import reverse_lazy as reverse
import pytest
from rest_framework import status

from swh.deposit.config import COL_IRI, DEPOSIT_STATUS_DEPOSITED
from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import (
    check_archive,
    create_arborescence_archive,
    post_archive,
)


def test_post_deposit_binary_no_slug(
    authenticated_client, deposit_collection, sample_archive, deposit_user, mocker
):
    """Posting a binary deposit without slug header should generate one

    """
    id_ = str(uuid.uuid4())
    mocker.patch("uuid.uuid4", return_value=id_)

    url = reverse(COL_IRI, args=[deposit_collection.name])

    # when
    response = post_archive(
        authenticated_client, url, sample_archive, in_progress="false",
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.origin_url == deposit_user.provider_url + id_
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED


def test_post_deposit_binary_support(
    authenticated_client, deposit_collection, sample_archive
):
    """Binary upload with content-type not in [zip,x-tar] should return 415

    """
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    external_id = "some-external-id-1"

    # when
    response = authenticated_client.post(
        url,
        sample_archive,
        HTTP_SLUG=external_id,
        content_type="application/octet-stream",
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(external_id=external_id)


def test_post_deposit_binary_upload_ok(
    authenticated_client, deposit_collection, sample_archive
):
    """Binary upload with correct headers should return 201 with receipt

    """
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    external_id = "some-external-id-1"

    # when
    response = post_archive(
        authenticated_client,
        url,
        sample_archive,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
    )

    # then
    response_content = parse_xml(BytesIO(response.content))
    assert response.status_code == status.HTTP_201_CREATED
    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED
    assert deposit.external_id == external_id
    assert deposit.collection == deposit_collection
    assert deposit.swhid is None

    deposit_request = DepositRequest.objects.get(deposit=deposit)
    check_archive(sample_archive["name"], deposit_request.archive.name)

    assert deposit_request.metadata is None
    assert deposit_request.raw_metadata is None

    response_content = parse_xml(BytesIO(response.content))

    assert response_content["swh:deposit_archive"] == sample_archive["name"]
    assert int(response_content["swh:deposit_id"]) == deposit.id
    assert response_content["swh:deposit_status"] == deposit.status

    # deprecated tags
    assert response_content["atom:deposit_archive"] == sample_archive["name"]
    assert int(response_content["atom:deposit_id"]) == deposit.id
    assert response_content["atom:deposit_status"] == deposit.status

    from django.urls import reverse as reverse_strict

    edit_iri = reverse_strict("edit_iri", args=[deposit_collection.name, deposit.id])

    assert response._headers["location"] == (
        "Location",
        "http://testserver" + edit_iri,
    )


def test_post_deposit_binary_failure_unsupported_packaging_header(
    authenticated_client, deposit_collection, sample_archive
):
    """Bin deposit without supported content_disposition header returns 400

    """
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    external_id = "some-external-id"

    # when
    response = post_archive(
        authenticated_client,
        url,
        sample_archive,
        HTTP_SLUG=external_id,
        HTTP_PACKAGING="something-unsupported",
    )

    # then
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        b"The packaging provided something-unsupported is not supported"
        in response.content
    )

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(external_id=external_id)


def test_post_deposit_binary_upload_no_content_disposition_header(
    authenticated_client, deposit_collection, sample_archive
):
    """Binary upload without content_disposition header should return 400

    """
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    external_id = "some-external-id"

    # when
    response = post_archive(
        authenticated_client,
        url,
        sample_archive,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION=None,
    )

    # then
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"CONTENT_DISPOSITION header is mandatory" in response.content

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(external_id=external_id)


def test_post_deposit_mediation_not_supported(
    authenticated_client, deposit_collection, sample_archive
):
    """Binary upload with mediation should return a 412 response

    """
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    external_id = "some-external-id-1"

    # when
    response = post_archive(
        authenticated_client,
        url,
        sample_archive,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
        HTTP_ON_BEHALF_OF="someone",
    )

    # then
    assert response.status_code == status.HTTP_412_PRECONDITION_FAILED

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(external_id=external_id)


def test_post_deposit_binary_upload_fail_if_upload_size_limit_exceeded(
    authenticated_client, deposit_collection, sample_archive, tmp_path
):
    """Binary upload must not exceed the limit set up...

    """
    tmp_path = str(tmp_path)
    url = reverse(COL_IRI, args=[deposit_collection.name])

    archive = create_arborescence_archive(
        tmp_path, "archive2", "file2", b"some content in file", up_to_size=500
    )

    external_id = "some-external-id"

    # when
    response = post_archive(
        authenticated_client,
        url,
        archive,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert b"Upload size limit exceeded" in response.content

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(external_id=external_id)


def test_post_deposit_binary_upload_fail_if_content_length_missing(
    authenticated_client, deposit_collection, sample_archive, tmp_path
):
    """The Content-Length header is mandatory

    """
    tmp_path = str(tmp_path)
    url = reverse(COL_IRI, args=[deposit_collection.name])

    archive = create_arborescence_archive(
        tmp_path, "archive2", "file2", b"some content in file", up_to_size=500
    )

    external_id = "some-external-id"

    # when
    response = post_archive(
        authenticated_client,
        url,
        archive,
        CONTENT_LENGTH=None,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"the CONTENT_LENGTH header must be sent." in response.content

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(external_id=external_id)


def test_post_deposit_2_post_2_different_deposits(
    authenticated_client, deposit_collection, sample_archive
):
    """2 posting deposits should return 2 different 201 with receipt

    """
    url = reverse(COL_IRI, args=[deposit_collection.name])

    # when
    response = post_archive(
        authenticated_client,
        url,
        sample_archive,
        HTTP_SLUG="some-external-id-1",
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)

    deposits = Deposit.objects.all()
    assert len(deposits) == 1
    assert deposits[0] == deposit

    # second post
    response = post_archive(
        authenticated_client,
        url,
        sample_archive,
        content_type="application/x-tar",
        HTTP_SLUG="another-external-id",
        HTTP_IN_PROGRESS="false",
    )

    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id2 = response_content["swh:deposit_id"]

    deposit2 = Deposit.objects.get(pk=deposit_id2)

    assert deposit != deposit2

    deposits = Deposit.objects.all().order_by("id")
    assert len(deposits) == 2
    assert list(deposits), [deposit == deposit2]
