# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.urls import reverse
from io import BytesIO
from rest_framework import status

from swh.deposit.config import COL_IRI, DEPOSIT_STATUS_DEPOSITED
from swh.deposit.models import Deposit, DepositRequest
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import check_archive


def test_post_deposit_multipart_without_slug_header_is_bad_request(
    authenticated_client, deposit_collection, atom_dataset
):
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    archive_content = b"some content representing archive"
    archive = InMemoryUploadedFile(
        BytesIO(archive_content),
        field_name="archive0",
        name="archive0",
        content_type="application/zip",
        size=len(archive_content),
        charset=None,
    )

    data_atom_entry = atom_dataset["entry-data-deposit-binary"]
    atom_entry = InMemoryUploadedFile(
        BytesIO(data_atom_entry.encode("utf-8")),
        field_name="atom0",
        name="atom0",
        content_type='application/atom+xml; charset="utf-8"',
        size=len(data_atom_entry),
        charset="utf-8",
    )

    # when
    response = authenticated_client.post(
        url,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
        # + headers
        HTTP_IN_PROGRESS="false",
    )

    assert b"Missing SLUG header" in response.content
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_post_deposit_multipart_zip(
    authenticated_client, deposit_collection, atom_dataset, sample_archive
):
    """one multipart deposit (zip+xml) should be accepted

    """
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    archive = InMemoryUploadedFile(
        BytesIO(sample_archive["data"]),
        field_name=sample_archive["name"],
        name=sample_archive["name"],
        content_type="application/zip",
        size=sample_archive["length"],
        charset=None,
    )

    data_atom_entry = atom_dataset["entry-data-deposit-binary"]
    atom_entry = InMemoryUploadedFile(
        BytesIO(data_atom_entry.encode("utf-8")),
        field_name="atom0",
        name="atom0",
        content_type='application/atom+xml; charset="utf-8"',
        size=len(data_atom_entry),
        charset="utf-8",
    )

    external_id = "external-id"

    # when
    response = authenticated_client.post(
        url,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
        # + headers
        HTTP_IN_PROGRESS="false",
        HTTP_SLUG=external_id,
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

    deposit_requests = DepositRequest.objects.filter(deposit=deposit)
    assert len(deposit_requests) == 2
    for deposit_request in deposit_requests:
        assert deposit_request.deposit == deposit
        if deposit_request.type == "archive":
            check_archive(sample_archive["name"], deposit_request.archive.name)
            assert deposit_request.metadata is None
            assert deposit_request.raw_metadata is None
        else:
            assert (
                deposit_request.metadata["id"]
                == "urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a"
            )
            assert deposit_request.raw_metadata == data_atom_entry


def test_post_deposit_multipart_tar(
    authenticated_client, deposit_collection, atom_dataset, sample_archive
):
    """one multipart deposit (tar+xml) should be accepted

    """
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    # from django.core.files import uploadedfile
    data_atom_entry = atom_dataset["entry-data-deposit-binary"]

    archive = InMemoryUploadedFile(
        BytesIO(sample_archive["data"]),
        field_name=sample_archive["name"],
        name=sample_archive["name"],
        content_type="application/x-tar",
        size=sample_archive["length"],
        charset=None,
    )

    atom_entry = InMemoryUploadedFile(
        BytesIO(data_atom_entry.encode("utf-8")),
        field_name="atom0",
        name="atom0",
        content_type='application/atom+xml; charset="utf-8"',
        size=len(data_atom_entry),
        charset="utf-8",
    )

    external_id = "external-id"

    # when
    response = authenticated_client.post(
        url,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
        # + headers
        HTTP_IN_PROGRESS="false",
        HTTP_SLUG=external_id,
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

    deposit_requests = DepositRequest.objects.filter(deposit=deposit)
    assert len(deposit_requests) == 2
    for deposit_request in deposit_requests:
        assert deposit_request.deposit == deposit
        if deposit_request.type == "archive":
            check_archive(sample_archive["name"], deposit_request.archive.name)
            assert deposit_request.metadata is None
            assert deposit_request.raw_metadata is None
        else:
            assert (
                deposit_request.metadata["id"]
                == "urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a"
            )
            assert deposit_request.raw_metadata == data_atom_entry


def test_post_deposit_multipart_put_to_replace_metadata(
    authenticated_client, deposit_collection, atom_dataset, sample_archive
):
    """One multipart deposit followed by a metadata update should be
       accepted

    """
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    data_atom_entry = atom_dataset["entry-data-deposit-binary"]

    archive = InMemoryUploadedFile(
        BytesIO(sample_archive["data"]),
        field_name=sample_archive["name"],
        name=sample_archive["name"],
        content_type="application/zip",
        size=sample_archive["length"],
        charset=None,
    )

    atom_entry = InMemoryUploadedFile(
        BytesIO(data_atom_entry.encode("utf-8")),
        field_name="atom0",
        name="atom0",
        content_type='application/atom+xml; charset="utf-8"',
        size=len(data_atom_entry),
        charset="utf-8",
    )

    external_id = "external-id"

    # when
    response = authenticated_client.post(
        url,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
        # + headers
        HTTP_IN_PROGRESS="true",
        HTTP_SLUG=external_id,
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

    deposit_requests = DepositRequest.objects.filter(deposit=deposit)

    assert len(deposit_requests) == 2
    for deposit_request in deposit_requests:
        assert deposit_request.deposit == deposit
        if deposit_request.type == "archive":
            check_archive(sample_archive["name"], deposit_request.archive.name)
        else:
            assert (
                deposit_request.metadata["id"]
                == "urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a"
            )
            assert deposit_request.raw_metadata == data_atom_entry

    replace_metadata_uri = response._headers["location"][1]
    response = authenticated_client.put(
        replace_metadata_uri,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-deposit-binary"],
        HTTP_IN_PROGRESS="false",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # deposit_id did not change
    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED
    assert deposit.external_id == external_id
    assert deposit.collection == deposit_collection
    assert deposit.swh_id is None

    deposit_requests = DepositRequest.objects.filter(deposit=deposit)
    assert len(deposit_requests) == 2
    for deposit_request in deposit_requests:
        assert deposit_request.deposit == deposit
        if deposit_request.type == "archive":
            check_archive(sample_archive["name"], deposit_request.archive.name)
        else:
            assert (
                deposit_request.metadata["id"]
                == "urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a"
            )
            assert (
                deposit_request.raw_metadata
                == atom_dataset["entry-data-deposit-binary"]
            )


# FAILURE scenarios


def test_post_deposit_multipart_only_archive_and_atom_entry(
    authenticated_client, deposit_collection
):
    """Multipart deposit only accepts one archive and one atom+xml"""
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    archive_content = b"some content representing archive"
    archive = InMemoryUploadedFile(
        BytesIO(archive_content),
        field_name="archive0",
        name="archive0",
        content_type="application/x-tar",
        size=len(archive_content),
        charset=None,
    )

    other_archive_content = b"some-other-content"
    other_archive = InMemoryUploadedFile(
        BytesIO(other_archive_content),
        field_name="atom0",
        name="atom0",
        content_type="application/x-tar",
        size=len(other_archive_content),
        charset="utf-8",
    )

    # when
    response = authenticated_client.post(
        url,
        format="multipart",
        data={"archive": archive, "atom_entry": other_archive,},
        # + headers
        HTTP_IN_PROGRESS="false",
        HTTP_SLUG="external-id",
    )

    # then
    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert (
        "Only 1 application/zip (or application/x-tar) archive"
        in response.content.decode("utf-8")
    )

    # when
    archive.seek(0)
    response = authenticated_client.post(
        url,
        format="multipart",
        data={"archive": archive,},
        # + headers
        HTTP_IN_PROGRESS="false",
        HTTP_SLUG="external-id",
    )

    # then
    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert (
        "You must provide both 1 application/zip (or "
        "application/x-tar) and 1 atom+xml entry for "
        "multipart deposit" in response.content.decode("utf-8")
    ) is True


def test_post_deposit_multipart_400_when_badly_formatted_xml(
    authenticated_client, deposit_collection, sample_archive, atom_dataset
):
    # given
    url = reverse(COL_IRI, args=[deposit_collection.name])

    archive_content = sample_archive["data"]
    archive = InMemoryUploadedFile(
        BytesIO(archive_content),
        field_name=sample_archive["name"],
        name=sample_archive["name"],
        content_type="application/zip",
        size=len(archive_content),
        charset=None,
    )

    data_atom_entry_ko = atom_dataset["entry-data-ko"]
    atom_entry = InMemoryUploadedFile(
        BytesIO(data_atom_entry_ko.encode("utf-8")),
        field_name="atom0",
        name="atom0",
        content_type='application/atom+xml; charset="utf-8"',
        size=len(data_atom_entry_ko),
        charset="utf-8",
    )

    # when
    response = authenticated_client.post(
        url,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
        # + headers
        HTTP_IN_PROGRESS="false",
        HTTP_SLUG="external-id",
    )

    assert b"Malformed xml metadata" in response.content
    assert response.status_code == status.HTTP_400_BAD_REQUEST
