# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.urls import reverse
from io import BytesIO

from rest_framework import status

from swh.deposit.config import (
    COL_IRI,
    EM_IRI,
    DEPOSIT_STATUS_DEPOSITED,
)
from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import create_arborescence_archive, check_archive


def test_post_deposit_binary_no_slug(
    authenticated_client, deposit_collection, sample_archive
):
    """Posting a binary deposit without slug header should return 400

    """
    url = reverse(COL_IRI, args=[deposit_collection.name])

    # when
    response = authenticated_client.post(
        url,
        content_type="application/zip",  # as zip
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
    )

    assert b"Missing SLUG header" in response.content
    assert response.status_code == status.HTTP_400_BAD_REQUEST


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
        content_type="application/octet-stream",
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
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
    response = authenticated_client.post(
        url,
        content_type="application/zip",  # as zip
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        # other headers needs HTTP_ prefix to be taken into account
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=%s" % (sample_archive["name"],),
    )

    # then
    response_content = parse_xml(BytesIO(response.content))
    assert response.status_code == status.HTTP_201_CREATED
    deposit_id = response_content["deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED
    assert deposit.external_id == external_id
    assert deposit.collection == deposit_collection
    assert deposit.swh_id is None

    deposit_request = DepositRequest.objects.get(deposit=deposit)
    check_archive(sample_archive["name"], deposit_request.archive.name)

    assert deposit_request.metadata is None
    assert deposit_request.raw_metadata is None

    response_content = parse_xml(BytesIO(response.content))
    assert response_content["deposit_archive"] == sample_archive["name"]
    assert int(response_content["deposit_id"]) == deposit.id
    assert response_content["deposit_status"] == deposit.status

    edit_se_iri = reverse("edit_se_iri", args=[deposit_collection.name, deposit.id])

    assert response._headers["location"] == (
        "Location",
        "http://testserver" + edit_se_iri,
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
    response = authenticated_client.post(
        url,
        content_type="application/zip",
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="something-unsupported",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
    )

    # then
    assert response.status_code == status.HTTP_400_BAD_REQUEST
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
    response = authenticated_client.post(
        url,
        content_type="application/zip",
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
    )

    # then
    assert response.status_code == status.HTTP_400_BAD_REQUEST
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
    response = authenticated_client.post(
        url,
        content_type="application/zip",
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_ON_BEHALF_OF="someone",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
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
    response = authenticated_client.post(
        url,
        content_type="application/zip",
        data=archive["data"],
        # + headers
        CONTENT_LENGTH=archive["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
    )

    # then
    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    assert b"Upload size limit exceeded" in response.content

    with pytest.raises(Deposit.DoesNotExist):
        Deposit.objects.get(external_id=external_id)


def test_post_deposit_2_post_2_different_deposits(
    authenticated_client, deposit_collection, sample_archive
):
    """2 posting deposits should return 2 different 201 with receipt

    """
    url = reverse(COL_IRI, args=[deposit_collection.name])

    # when
    response = authenticated_client.post(
        url,
        content_type="application/zip",  # as zip
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        HTTP_SLUG="some-external-id-1",
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)

    deposits = Deposit.objects.all()
    assert len(deposits) == 1
    assert deposits[0] == deposit

    # second post
    response = authenticated_client.post(
        url,
        content_type="application/x-tar",  # as zip
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        HTTP_SLUG="another-external-id",
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename1",
    )

    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id2 = response_content["deposit_id"]

    deposit2 = Deposit.objects.get(pk=deposit_id2)

    assert deposit != deposit2

    deposits = Deposit.objects.all().order_by("id")
    assert len(deposits) == 2
    assert list(deposits), [deposit == deposit2]


def test_post_deposit_binary_and_post_to_add_another_archive(
    authenticated_client, deposit_collection, sample_archive, tmp_path
):
    """Updating a deposit should return a 201 with receipt

    """
    tmp_path = str(tmp_path)
    url = reverse(COL_IRI, args=[deposit_collection.name])

    external_id = "some-external-id-1"

    # when
    response = authenticated_client.post(
        url,
        content_type="application/zip",  # as zip
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="true",
        HTTP_CONTENT_DISPOSITION="attachment; filename=%s" % (sample_archive["name"],),
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.status == "partial"
    assert deposit.external_id == external_id
    assert deposit.collection == deposit_collection
    assert deposit.swh_id is None

    deposit_request = DepositRequest.objects.get(deposit=deposit)
    assert deposit_request.deposit == deposit
    assert deposit_request.type == "archive"
    check_archive(sample_archive["name"], deposit_request.archive.name)

    # 2nd archive to upload
    archive2 = create_arborescence_archive(
        tmp_path, "archive2", "file2", b"some other content in file"
    )

    # uri to update the content
    update_uri = reverse(EM_IRI, args=[deposit_collection.name, deposit_id])

    # adding another archive for the deposit and finalizing it
    response = authenticated_client.post(
        update_uri,
        content_type="application/zip",  # as zip
        data=archive2["data"],
        # + headers
        CONTENT_LENGTH=archive2["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=archive2["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_CONTENT_DISPOSITION="attachment; filename=%s" % (archive2["name"]),
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED
    assert deposit.external_id == external_id
    assert deposit.collection == deposit_collection
    assert deposit.swh_id is None

    deposit_requests = list(
        DepositRequest.objects.filter(deposit=deposit).order_by("id")
    )

    # 2 deposit requests for the same deposit
    assert len(deposit_requests) == 2
    assert deposit_requests[0].deposit == deposit
    assert deposit_requests[0].type == "archive"
    check_archive(sample_archive["name"], deposit_requests[0].archive.name)

    assert deposit_requests[1].deposit == deposit
    assert deposit_requests[1].type == "archive"
    check_archive(archive2["name"], deposit_requests[1].archive.name)

    # only 1 deposit in db
    deposits = Deposit.objects.all()
    assert len(deposits) == 1


def test_post_deposit_then_update_refused(
    authenticated_client, deposit_collection, sample_archive, atom_dataset, tmp_path
):
    """Updating a deposit with status 'ready' should return a 400

    """
    tmp_path = str(tmp_path)
    url = reverse(COL_IRI, args=[deposit_collection.name])

    external_id = "some-external-id-1"

    # when
    response = authenticated_client.post(
        url,
        content_type="application/zip",  # as zip
        data=sample_archive["data"],
        # + headers
        CONTENT_LENGTH=sample_archive["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=sample_archive["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED
    assert deposit.external_id == external_id
    assert deposit.collection == deposit_collection
    assert deposit.swh_id is None

    deposit_request = DepositRequest.objects.get(deposit=deposit)
    assert deposit_request.deposit == deposit
    check_archive("filename0", deposit_request.archive.name)

    # updating/adding is forbidden

    # uri to update the content
    edit_se_iri = reverse("edit_se_iri", args=[deposit_collection.name, deposit_id])
    em_iri = reverse("em_iri", args=[deposit_collection.name, deposit_id])

    # Testing all update/add endpoint should fail
    # since the status is ready

    archive2 = create_arborescence_archive(
        tmp_path, "archive2", "file2", b"some content in file 2"
    )

    # replacing file is no longer possible since the deposit's
    # status is ready
    r = authenticated_client.put(
        em_iri,
        content_type="application/zip",
        data=archive2["data"],
        CONTENT_LENGTH=archive2["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=archive2["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST

    # adding file is no longer possible since the deposit's status
    # is ready
    r = authenticated_client.post(
        em_iri,
        content_type="application/zip",
        data=archive2["data"],
        CONTENT_LENGTH=archive2["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=archive2["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=filename0",
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST

    # replacing metadata is no longer possible since the deposit's
    # status is ready
    r = authenticated_client.put(
        edit_se_iri,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-deposit-binary"],
        CONTENT_LENGTH=len(atom_dataset["entry-data-deposit-binary"]),
        HTTP_SLUG=external_id,
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST

    # adding new metadata is no longer possible since the
    # deposit's status is ready
    r = authenticated_client.post(
        edit_se_iri,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-deposit-binary"],
        CONTENT_LENGTH=len(atom_dataset["entry-data-deposit-binary"]),
        HTTP_SLUG=external_id,
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST

    archive_content = b"some content representing archive"
    archive = InMemoryUploadedFile(
        BytesIO(archive_content),
        field_name="archive0",
        name="archive0",
        content_type="application/zip",
        size=len(archive_content),
        charset=None,
    )

    atom_entry = InMemoryUploadedFile(
        BytesIO(atom_dataset["entry-data-deposit-binary"].encode("utf-8")),
        field_name="atom0",
        name="atom0",
        content_type='application/atom+xml; charset="utf-8"',
        size=len(atom_dataset["entry-data-deposit-binary"]),
        charset="utf-8",
    )

    # replacing multipart metadata is no longer possible since the
    # deposit's status is ready
    r = authenticated_client.put(
        edit_se_iri,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST

    # adding new metadata is no longer possible since the
    # deposit's status is ready
    r = authenticated_client.post(
        edit_se_iri,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST
