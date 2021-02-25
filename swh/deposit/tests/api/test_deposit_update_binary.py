# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Tests updates on EM-IRI"""

from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.urls import reverse_lazy as reverse
from rest_framework import status

from swh.deposit.config import COL_IRI, DEPOSIT_STATUS_DEPOSITED, EM_IRI, SE_IRI
from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import (
    check_archive,
    create_arborescence_archive,
    post_archive,
    post_atom,
    put_archive,
    put_atom,
)


def test_post_deposit_binary_and_post_to_add_another_archive(
    authenticated_client, deposit_collection, sample_archive, tmp_path
):
    """Updating a deposit should return a 201 with receipt

    """
    tmp_path = str(tmp_path)
    url = reverse(COL_IRI, args=[deposit_collection.name])

    external_id = "some-external-id-1"

    # when
    response = post_archive(
        authenticated_client,
        url,
        sample_archive,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="true",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.status == "partial"
    assert deposit.external_id == external_id
    assert deposit.collection == deposit_collection
    assert deposit.swhid is None

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
    response = post_archive(
        authenticated_client, update_uri, archive2, HTTP_SLUG=external_id,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED
    assert deposit.external_id == external_id
    assert deposit.collection == deposit_collection
    assert deposit.swhid is None

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


def test_replace_archive_to_deposit_is_possible(
    tmp_path,
    partial_deposit,
    deposit_collection,
    authenticated_client,
    sample_archive,
    atom_dataset,
):
    """Replace all archive with another one should return a 204 response

    """
    tmp_path = str(tmp_path)
    # given
    deposit = partial_deposit
    requests = DepositRequest.objects.filter(deposit=deposit, type="archive")

    assert len(list(requests)) == 1
    check_archive(sample_archive["name"], requests[0].archive.name)

    # we have no metadata for that deposit
    requests = list(DepositRequest.objects.filter(deposit=deposit, type="metadata"))
    assert len(requests) == 0

    response = post_atom(
        authenticated_client,
        reverse(SE_IRI, args=[deposit_collection.name, deposit.id]),
        data=atom_dataset["entry-data1"],
        HTTP_SLUG=deposit.external_id,
        HTTP_IN_PROGRESS=True,
    )

    requests = list(DepositRequest.objects.filter(deposit=deposit, type="metadata"))
    assert len(requests) == 1

    update_uri = reverse(EM_IRI, args=[deposit_collection.name, deposit.id])
    external_id = "some-external-id-1"
    archive2 = create_arborescence_archive(
        tmp_path, "archive2", "file2", b"some other content in file"
    )

    response = put_archive(
        authenticated_client,
        update_uri,
        archive2,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    requests = DepositRequest.objects.filter(deposit=deposit, type="archive")

    assert len(list(requests)) == 1
    check_archive(archive2["name"], requests[0].archive.name)

    # check we did not touch the other parts
    requests = list(DepositRequest.objects.filter(deposit=deposit, type="metadata"))
    assert len(requests) == 1


def test_add_archive_to_unknown_deposit(
    authenticated_client, deposit_collection, atom_dataset
):
    """Adding metadata to unknown deposit should return a 404 response

    """
    unknown_deposit_id = 997
    try:
        Deposit.objects.get(pk=unknown_deposit_id)
    except Deposit.DoesNotExist:
        assert True

    url = reverse(EM_IRI, args=[deposit_collection.name, unknown_deposit_id])
    response = authenticated_client.post(
        url, content_type="application/zip", data=atom_dataset["entry-data1"]
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_content = parse_xml(response.content)
    assert (
        "Deposit %s does not exist" % unknown_deposit_id
        == response_content["sword:error"]["atom:summary"]
    )


def test_replace_archive_to_unknown_deposit(
    authenticated_client, deposit_collection, atom_dataset
):
    """Replacing archive to unknown deposit should return a 404 response

    """
    unknown_deposit_id = 996
    try:
        Deposit.objects.get(pk=unknown_deposit_id)
    except Deposit.DoesNotExist:
        assert True

    url = reverse(EM_IRI, args=[deposit_collection.name, unknown_deposit_id])
    response = authenticated_client.put(
        url, content_type="application/zip", data=atom_dataset["entry-data1"]
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_content = parse_xml(response.content)
    assert (
        "Deposit %s does not exist" % unknown_deposit_id
        == response_content["sword:error"]["atom:summary"]
    )


def test_add_archive_to_deposit_is_possible(
    tmp_path,
    authenticated_client,
    deposit_collection,
    partial_deposit_with_metadata,
    sample_archive,
):
    """Add another archive to a deposit return a 201 response

    """
    tmp_path = str(tmp_path)
    deposit = partial_deposit_with_metadata

    requests = DepositRequest.objects.filter(deposit=deposit, type="archive")

    assert len(requests) == 1
    check_archive(sample_archive["name"], requests[0].archive.name)

    requests_meta0 = DepositRequest.objects.filter(deposit=deposit, type="metadata")
    assert len(requests_meta0) == 1

    update_uri = reverse(EM_IRI, args=[deposit_collection.name, deposit.id])

    external_id = "some-external-id-1"
    archive2 = create_arborescence_archive(
        tmp_path, "archive2", "file2", b"some other content in file"
    )

    response = post_archive(
        authenticated_client,
        update_uri,
        archive2,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
    )

    assert response.status_code == status.HTTP_201_CREATED

    requests = DepositRequest.objects.filter(deposit=deposit, type="archive").order_by(
        "id"
    )

    assert len(requests) == 2
    # first archive still exists
    check_archive(sample_archive["name"], requests[0].archive.name)
    # a new one was added
    check_archive(archive2["name"], requests[1].archive.name)

    # check we did not touch the other parts
    requests_meta1 = DepositRequest.objects.filter(deposit=deposit, type="metadata")
    assert len(requests_meta1) == 1
    assert set(requests_meta0) == set(requests_meta1)


def test_post_deposit_then_update_refused(
    authenticated_client, deposit_collection, sample_archive, atom_dataset, tmp_path
):
    """Updating a deposit with status 'ready' should return a 400

    """
    tmp_path = str(tmp_path)
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
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = response_content["swh:deposit_id"]

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED
    assert deposit.external_id == external_id
    assert deposit.collection == deposit_collection
    assert deposit.swhid is None

    deposit_request = DepositRequest.objects.get(deposit=deposit)
    assert deposit_request.deposit == deposit
    check_archive(sample_archive["name"], deposit_request.archive.name)

    # updating/adding is forbidden

    # uri to update the content
    edit_iri = reverse("edit_iri", args=[deposit_collection.name, deposit_id])
    se_iri = reverse("se_iri", args=[deposit_collection.name, deposit_id])
    em_iri = reverse("em_iri", args=[deposit_collection.name, deposit_id])

    # Testing all update/add endpoint should fail
    # since the status is ready

    archive2 = create_arborescence_archive(
        tmp_path, "archive2", "file2", b"some content in file 2"
    )

    # replacing file is no longer possible since the deposit's
    # status is ready
    r = put_archive(
        authenticated_client,
        em_iri,
        archive2,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert b"You can only act on deposit with status &#39;partial&#39;" in r.content

    # adding file is no longer possible since the deposit's status
    # is ready
    r = post_archive(
        authenticated_client,
        em_iri,
        archive2,
        HTTP_SLUG=external_id,
        HTTP_IN_PROGRESS="false",
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert b"You can only act on deposit with status &#39;partial&#39;" in r.content

    # replacing metadata is no longer possible since the deposit's
    # status is ready
    r = put_atom(
        authenticated_client,
        edit_iri,
        data=atom_dataset["entry-data-deposit-binary"],
        CONTENT_LENGTH=len(atom_dataset["entry-data-deposit-binary"]),
        HTTP_SLUG=external_id,
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert b"You can only act on deposit with status &#39;partial&#39;" in r.content

    # adding new metadata is no longer possible since the
    # deposit's status is ready
    r = post_atom(
        authenticated_client,
        se_iri,
        data=atom_dataset["entry-data-deposit-binary"],
        CONTENT_LENGTH=len(atom_dataset["entry-data-deposit-binary"]),
        HTTP_SLUG=external_id,
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert b"You can only act on deposit with status &#39;partial&#39;" in r.content

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
        edit_iri,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert b"You can only act on deposit with status &#39;partial&#39;" in r.content

    # adding new metadata is no longer possible since the
    # deposit's status is ready
    r = authenticated_client.post(
        se_iri,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
    )

    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert b"You can only act on deposit with status &#39;partial&#39;" in r.content
