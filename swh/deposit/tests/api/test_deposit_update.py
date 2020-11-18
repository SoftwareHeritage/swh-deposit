# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from io import BytesIO

import attr
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.urls import reverse
from rest_framework import status

from swh.deposit.api.common import ACCEPT_ARCHIVE_CONTENT_TYPES
from swh.deposit.config import (
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_PARTIAL,
    EDIT_SE_IRI,
    EM_IRI,
    APIConfig,
)
from swh.deposit.models import Deposit, DepositCollection, DepositRequest
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import check_archive, create_arborescence_archive
from swh.model.hashutil import hash_to_bytes
from swh.model.identifiers import parse_swhid, swhid
from swh.model.model import (
    MetadataAuthority,
    MetadataAuthorityType,
    MetadataFetcher,
    MetadataTargetType,
    RawExtrinsicMetadata,
)
from swh.storage.interface import PagedResult


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


def test_add_both_archive_and_metadata_to_deposit(
    authenticated_client,
    deposit_collection,
    partial_deposit_with_metadata,
    atom_dataset,
    sample_archive,
):
    """Scenario: Add both a new archive and new metadata to a partial deposit is ok

    Response: 201

    """
    deposit = partial_deposit_with_metadata
    requests = DepositRequest.objects.filter(deposit=deposit, type="metadata")
    assert len(requests) == 1

    requests_archive0 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive0) == 1

    update_uri = reverse(EDIT_SE_IRI, args=[deposit_collection.name, deposit.id])
    archive = InMemoryUploadedFile(
        BytesIO(sample_archive["data"]),
        field_name=sample_archive["name"],
        name=sample_archive["name"],
        content_type="application/x-tar",
        size=sample_archive["length"],
        charset=None,
    )

    data_atom_entry = atom_dataset["entry-data1"]
    atom_entry = InMemoryUploadedFile(
        BytesIO(data_atom_entry.encode("utf-8")),
        field_name="atom0",
        name="atom0",
        content_type='application/atom+xml; charset="utf-8"',
        size=len(data_atom_entry),
        charset="utf-8",
    )

    update_uri = reverse(EDIT_SE_IRI, args=[deposit_collection.name, deposit.id])
    response = authenticated_client.post(
        update_uri,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
    )

    assert response.status_code == status.HTTP_201_CREATED
    requests = DepositRequest.objects.filter(deposit=deposit, type="metadata").order_by(
        "id"
    )

    assert len(requests) == 1 + 1, "New deposit request archive got added"
    expected_raw_meta0 = atom_dataset["entry-data0"] % (
        deposit.external_id.encode("utf-8")
    )
    # a new one was added
    assert requests[0].raw_metadata == expected_raw_meta0
    assert requests[1].raw_metadata == data_atom_entry

    # check we did not touch the other parts
    requests_archive1 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive1) == 1 + 1, "New deposit request metadata got added"


def test_post_metadata_empty_post_finalize_deposit_ok(
    authenticated_client,
    deposit_collection,
    partial_deposit_with_metadata,
    atom_dataset,
):
    """Empty atom post entry with header in-progress to false transitions deposit to
       'deposited' status

    Response: 200

    """
    deposit = partial_deposit_with_metadata
    assert deposit.status == DEPOSIT_STATUS_PARTIAL

    update_uri = reverse(EDIT_SE_IRI, args=[deposit_collection.name, deposit.id])
    response = authenticated_client.post(
        update_uri,
        content_type="application/atom+xml;type=entry",
        data="",
        size=0,
        HTTP_IN_PROGRESS=False,
    )

    assert response.status_code == status.HTTP_200_OK
    deposit = Deposit.objects.get(pk=deposit.id)
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED


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
    assert b"Packaging format supported is restricted" in response.content
    for supported_format in ACCEPT_ARCHIVE_CONTENT_TYPES:
        assert supported_format.encode() in response.content


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
    assert b"Packaging format supported is restricted" in response.content
    for supported_format in ACCEPT_ARCHIVE_CONTENT_TYPES:
        assert supported_format.encode() in response.content


def test_put_update_metadata_and_archive_deposit_partial_nominal(
    tmp_path,
    authenticated_client,
    partial_deposit_with_metadata,
    deposit_collection,
    atom_dataset,
    sample_archive,
):
    """Scenario: Replace metadata and archive(s) with new ones should be ok

    Response: 204

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

    archive = InMemoryUploadedFile(
        BytesIO(sample_archive["data"]),
        field_name=sample_archive["name"],
        name=sample_archive["name"],
        content_type="application/x-tar",
        size=sample_archive["length"],
        charset=None,
    )

    data_atom_entry = atom_dataset["entry-data1"]
    atom_entry = InMemoryUploadedFile(
        BytesIO(data_atom_entry.encode("utf-8")),
        field_name="atom0",
        name="atom0",
        content_type='application/atom+xml; charset="utf-8"',
        size=len(data_atom_entry),
        charset="utf-8",
    )

    update_uri = reverse(EDIT_SE_IRI, args=[deposit_collection.name, deposit.id])
    response = authenticated_client.put(
        update_uri,
        format="multipart",
        data={"archive": archive, "atom_entry": atom_entry,},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # check we updated the metadata part
    requests_meta = DepositRequest.objects.filter(deposit=deposit, type="metadata")
    assert len(requests_meta) == 1
    request_meta1 = requests_meta[0]
    raw_metadata1 = request_meta1.raw_metadata
    assert raw_metadata1 == data_atom_entry
    assert raw_metadata0 != raw_metadata1
    assert request_meta0 != request_meta1

    # and the archive part
    requests_archive1 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive1) == 1
    assert set(requests_archive0) != set(requests_archive1)


def test_put_update_metadata_done_deposit_nominal(
    tmp_path,
    authenticated_client,
    complete_deposit,
    deposit_collection,
    atom_dataset,
    sample_data,
    swh_storage,
):
    """Nominal scenario, client send an update of metadata on a deposit with status "done"
       with an existing swhid. Such swhid has its metadata updated accordingly both in
       the deposit backend and in the metadata storage.

       Response: 204

    """
    deposit_swhid = parse_swhid(complete_deposit.swhid)
    assert deposit_swhid.object_type == "directory"
    directory_id = hash_to_bytes(deposit_swhid.object_id)

    # directory targeted by the complete_deposit does not exist in the storage
    assert list(swh_storage.directory_missing([directory_id])) == [directory_id]

    # so let's create a directory reference in the storage (current deposit targets an
    # unknown swhid)
    existing_directory = sample_data.directory
    swh_storage.directory_add([existing_directory])
    assert list(swh_storage.directory_missing([existing_directory.id])) == []

    # and patch one complete deposit swhid so it targets said reference
    complete_deposit.swhid = swhid("directory", existing_directory.id)
    complete_deposit.save()

    actual_existing_requests_archive = DepositRequest.objects.filter(
        deposit=complete_deposit, type="archive"
    )
    nb_archives = len(actual_existing_requests_archive)
    actual_existing_requests_metadata = DepositRequest.objects.filter(
        deposit=complete_deposit, type="metadata"
    )
    nb_metadata = len(actual_existing_requests_metadata)

    update_uri = reverse(
        EDIT_SE_IRI, args=[deposit_collection.name, complete_deposit.id]
    )
    response = authenticated_client.put(
        update_uri,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data1"],
        HTTP_X_CHECK_SWHID=complete_deposit.swhid,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    new_requests_meta = DepositRequest.objects.filter(
        deposit=complete_deposit, type="metadata"
    )
    assert len(new_requests_meta) == nb_metadata + 1
    request_meta1 = new_requests_meta[0]
    raw_metadata1 = request_meta1.raw_metadata
    assert raw_metadata1 == atom_dataset["entry-data1"]

    # check we did not touch the other parts
    requests_archive1 = DepositRequest.objects.filter(
        deposit=complete_deposit, type="archive"
    )
    assert len(requests_archive1) == nb_archives
    assert set(actual_existing_requests_archive) == set(requests_archive1)

    # Ensure metadata stored in the metadata storage is consistent
    metadata_authority = MetadataAuthority(
        type=MetadataAuthorityType.DEPOSIT_CLIENT,
        url=complete_deposit.client.provider_url,
        metadata={"name": complete_deposit.client.last_name},
    )

    actual_authority = swh_storage.metadata_authority_get(
        MetadataAuthorityType.DEPOSIT_CLIENT, url=complete_deposit.client.provider_url
    )
    assert actual_authority == metadata_authority

    config = APIConfig()
    metadata_fetcher = MetadataFetcher(
        name=config.tool["name"],
        version=config.tool["version"],
        metadata=config.tool["configuration"],
    )

    actual_fetcher = swh_storage.metadata_fetcher_get(
        config.tool["name"], config.tool["version"]
    )
    assert actual_fetcher == metadata_fetcher

    directory_swhid = parse_swhid(complete_deposit.swhid)
    page_results = swh_storage.raw_extrinsic_metadata_get(
        MetadataTargetType.DIRECTORY, directory_swhid, metadata_authority
    )
    assert page_results == PagedResult(
        results=[
            RawExtrinsicMetadata(
                type=MetadataTargetType.DIRECTORY,
                target=directory_swhid,
                discovery_date=request_meta1.date,
                authority=attr.evolve(metadata_authority, metadata=None),
                fetcher=attr.evolve(metadata_fetcher, metadata=None),
                format="sword-v2-atom-codemeta",
                metadata=raw_metadata1.encode(),
                origin=complete_deposit.origin_url,
            )
        ],
        next_page_token=None,
    )


def test_put_update_metadata_done_deposit_failure_mismatched_swhid(
    tmp_path,
    authenticated_client,
    complete_deposit,
    deposit_collection,
    atom_dataset,
    swh_storage,
):
    """failure: client updates metadata on deposit with SWHID not matching the deposit's.

       Response: 400

    """
    incorrect_swhid = "swh:1:dir:ef04a768181417fbc5eef4243e2507915f24deea"
    assert complete_deposit.swhid != incorrect_swhid

    update_uri = reverse(
        EDIT_SE_IRI, args=[deposit_collection.name, complete_deposit.id]
    )
    response = authenticated_client.put(
        update_uri,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data1"],
        HTTP_X_CHECK_SWHID=incorrect_swhid,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Mismatched provided SWHID" in response.content


def test_put_update_metadata_done_deposit_failure_malformed_xml(
    tmp_path,
    authenticated_client,
    complete_deposit,
    deposit_collection,
    atom_dataset,
    swh_storage,
):
    """failure: client updates metadata on deposit done with a malformed xml

       Response: 400

    """
    update_uri = reverse(
        EDIT_SE_IRI, args=[deposit_collection.name, complete_deposit.id]
    )
    response = authenticated_client.put(
        update_uri,
        content_type="application/atom+xml;type=entry",
        data=atom_dataset["entry-data-ko"],
        HTTP_X_CHECK_SWHID=complete_deposit.swhid,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Malformed xml metadata" in response.content


def test_put_update_metadata_done_deposit_failure_empty_xml(
    tmp_path,
    authenticated_client,
    complete_deposit,
    deposit_collection,
    atom_dataset,
    swh_storage,
):
    """failure: client updates metadata on deposit done with an empty xml.

       Response: 400

    """
    update_uri = reverse(
        EDIT_SE_IRI, args=[deposit_collection.name, complete_deposit.id]
    )

    for atom_key in ["entry-data-empty-body", "entry-data-empty-body-no-namespace"]:
        atom_content = atom_dataset[atom_key]
        response = authenticated_client.put(
            update_uri,
            content_type="application/atom+xml;type=entry",
            data=atom_content,
            HTTP_X_CHECK_SWHID=complete_deposit.swhid,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert b"Empty body request is not supported" in response.content


def test_put_update_metadata_done_deposit_failure_functional_checks(
    tmp_path,
    authenticated_client,
    complete_deposit,
    deposit_collection,
    atom_dataset,
    swh_storage,
):
    """failure: client updates metadata on deposit done without required incomplete metadata

       Response: 400

    """
    update_uri = reverse(
        EDIT_SE_IRI, args=[deposit_collection.name, complete_deposit.id]
    )

    response = authenticated_client.put(
        update_uri,
        content_type="application/atom+xml;type=entry",
        # no title, nor author, nor name fields
        data=atom_dataset["entry-data-fail-metadata-functional-checks"],
        HTTP_X_CHECK_SWHID=complete_deposit.swhid,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Functional metadata checks failure" in response.content
    # detail on the errors
    assert b"- Mandatory fields are missing (author)" in response.content
    assert (
        b"- Mandatory alternate fields are missing (name or title)" in response.content
    )
