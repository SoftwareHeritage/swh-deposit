# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.urls import reverse
from rest_framework import status

from swh.deposit.models import Deposit, DepositRequest, DepositCollection
from swh.deposit.config import EDIT_SE_IRI, EM_IRI
from swh.deposit.parsers import parse_xml

from swh.deposit.tests.common import create_arborescence_archive, check_archive


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

    response = authenticated_client.post(
        reverse(EDIT_SE_IRI, args=[deposit_collection.name, deposit.id]),
        content_type="application/atom+xml;type=entry",
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

    response = authenticated_client.put(
        update_uri,
        content_type="application/zip",  # as zip
        data=archive2["data"],
        # + headers
        CONTENT_LENGTH=archive2["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=archive2["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=%s" % (archive2["name"],),
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    requests = DepositRequest.objects.filter(deposit=deposit, type="archive")

    assert len(list(requests)) == 1
    check_archive(archive2["name"], requests[0].archive.name)

    # check we did not touch the other parts
    requests = list(DepositRequest.objects.filter(deposit=deposit, type="metadata"))
    assert len(requests) == 1


def test_replace_metadata_to_deposit_is_possible(
    tmp_path,
    authenticated_client,
    partial_deposit_with_metadata,
    deposit_collection,
    atom_dataset,
):
    """Replace all metadata with another one should return a 204 response

    """
    # given
    deposit = partial_deposit_with_metadata
    raw_metadata0 = atom_dataset["entry-data0"] % deposit.external_id.encode("utf-8")

    requests_meta = DepositRequest.objects.filter(deposit=deposit, type="metadata")
    assert len(requests_meta) == 1
    request_meta0 = requests_meta[0]
    assert request_meta0.raw_metadata == raw_metadata0

    requests_archive0 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive0) == 1

    update_uri = reverse(EDIT_SE_IRI, args=[deposit_collection.name, deposit.id])

    response = authenticated_client.put(
        update_uri,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data1"],
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    requests_meta = DepositRequest.objects.filter(deposit=deposit, type="metadata")

    assert len(requests_meta) == 1
    request_meta1 = requests_meta[0]
    raw_metadata1 = request_meta1.raw_metadata
    assert raw_metadata1 == atom_dataset["entry-data1"]
    assert raw_metadata0 != raw_metadata1
    assert request_meta0 != request_meta1

    # check we did not touch the other parts
    requests_archive1 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive1) == 1
    assert set(requests_archive0) == set(requests_archive1)


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

    response = authenticated_client.post(
        update_uri,
        content_type="application/zip",  # as zip
        data=archive2["data"],
        # + headers
        CONTENT_LENGTH=archive2["length"],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=archive2["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=%s" % (archive2["name"],),
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


def test_add_metadata_to_deposit_is_possible(
    authenticated_client,
    deposit_collection,
    partial_deposit_with_metadata,
    atom_dataset,
):
    """Add metadata with another one should return a 204 response

    """
    deposit = partial_deposit_with_metadata
    requests = DepositRequest.objects.filter(deposit=deposit, type="metadata")

    assert len(requests) == 1

    requests_archive0 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive0) == 1

    update_uri = reverse(EDIT_SE_IRI, args=[deposit_collection.name, deposit.id])

    atom_entry = atom_dataset["entry-data1"]
    response = authenticated_client.post(
        update_uri, content_type="application/atom+xml;type=entry", data=atom_entry
    )

    assert response.status_code == status.HTTP_201_CREATED

    requests = DepositRequest.objects.filter(deposit=deposit, type="metadata").order_by(
        "id"
    )

    assert len(requests) == 2
    expected_raw_meta0 = atom_dataset["entry-data0"] % (
        deposit.external_id.encode("utf-8")
    )
    # a new one was added
    assert requests[0].raw_metadata == expected_raw_meta0
    assert requests[1].raw_metadata == atom_entry

    # check we did not touch the other parts
    requests_archive1 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive1) == 1
    assert set(requests_archive0) == set(requests_archive1)


def test_add_metadata_to_unknown_deposit(
    deposit_collection, authenticated_client, atom_dataset
):
    """Replacing metadata to unknown deposit should return a 404 response

    """
    unknown_deposit_id = 1000
    try:
        Deposit.objects.get(pk=unknown_deposit_id)
    except Deposit.DoesNotExist:
        assert True

    url = reverse(EDIT_SE_IRI, args=[deposit_collection, unknown_deposit_id])
    response = authenticated_client.post(
        url,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data1"],
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_content = parse_xml(response.content)
    assert "Unknown collection name" in response_content["sword:error"]["summary"]


def test_add_metadata_to_unknown_collection(
    partial_deposit, authenticated_client, atom_dataset
):
    """Replacing metadata to unknown deposit should return a 404 response

    """
    deposit = partial_deposit
    unknown_collection_name = "unknown-collection"
    try:
        DepositCollection.objects.get(name=unknown_collection_name)
    except DepositCollection.DoesNotExist:
        assert True

    url = reverse(EDIT_SE_IRI, args=[unknown_collection_name, deposit.id])
    response = authenticated_client.post(
        url,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data1"],
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_content = parse_xml(response.content)
    assert "Unknown collection name" in response_content["sword:error"]["summary"]


def test_replace_metadata_to_unknown_deposit(
    authenticated_client, deposit_collection, atom_dataset
):
    """Adding metadata to unknown deposit should return a 404 response

    """
    unknown_deposit_id = 998
    try:
        Deposit.objects.get(pk=unknown_deposit_id)
    except Deposit.DoesNotExist:
        assert True
    url = reverse(EDIT_SE_IRI, args=[deposit_collection.name, unknown_deposit_id])
    response = authenticated_client.put(
        url,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data1"],
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_content = parse_xml(response.content)
    assert (
        "Deposit with id %s does not exist" % unknown_deposit_id
        == response_content["sword:error"]["summary"]
    )


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
        "Deposit with id %s does not exist" % unknown_deposit_id
        == response_content["sword:error"]["summary"]
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
        "Deposit with id %s does not exist" % unknown_deposit_id
        == response_content["sword:error"]["summary"]
    )


def test_post_metadata_to_em_iri_failure(
    authenticated_client, deposit_collection, partial_deposit, atom_dataset
):
    """Update (POST) archive with wrong content type should return 400

    """
    deposit = partial_deposit
    update_uri = reverse(EM_IRI, args=[deposit_collection.name, deposit.id])
    response = authenticated_client.post(
        update_uri,
        content_type="application/x-gtar-compressed",
        data=atom_dataset["entry-data1"],
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_content = parse_xml(response.content)
    msg = (
        "Packaging format supported is restricted to "
        + "application/zip, application/x-tar"
    )
    assert msg == response_content["sword:error"]["summary"]


def test_put_metadata_to_em_iri_failure(
    authenticated_client, deposit_collection, partial_deposit, atom_dataset
):
    """Update (PUT) archive with wrong content type should return 400

    """
    # given
    deposit = partial_deposit
    # when
    update_uri = reverse(EM_IRI, args=[deposit_collection.name, deposit.id])
    response = authenticated_client.put(
        update_uri,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data1"],
    )
    # then
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    response_content = parse_xml(response.content)
    msg = (
        "Packaging format supported is restricted to "
        + "application/zip, application/x-tar"
    )
    assert msg == response_content["sword:error"]["summary"]
