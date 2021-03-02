# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from io import BytesIO

import attr
from django.urls import reverse_lazy as reverse
import pytest
from rest_framework import status

from swh.deposit.api.common import ACCEPT_ARCHIVE_CONTENT_TYPES
from swh.deposit.config import (
    COL_IRI,
    DEPOSIT_STATUS_DEPOSITED,
    EDIT_IRI,
    EM_IRI,
    SE_IRI,
    APIConfig,
)
from swh.deposit.models import Deposit, DepositCollection, DepositRequest
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import post_atom, put_atom
from swh.model.hashutil import hash_to_bytes
from swh.model.identifiers import CoreSWHID, ExtendedSWHID, ObjectType
from swh.model.model import (
    MetadataAuthority,
    MetadataAuthorityType,
    MetadataFetcher,
    RawExtrinsicMetadata,
)
from swh.storage.interface import PagedResult


def test_post_deposit_atom_entry_multiple_steps(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """After initial deposit, updating a deposit should return a 201

    """
    # given
    origin_url = deposit_user.provider_url + "2225c695-cfb8-4ebb-aaaa-80da344efa6a"

    with pytest.raises(Deposit.DoesNotExist):
        deposit = Deposit.objects.get(origin_url=origin_url)

    # when
    response = post_atom(
        authenticated_client,
        reverse(COL_IRI, args=[deposit_collection.name]),
        data=atom_dataset["entry-data1"],
        HTTP_IN_PROGRESS="True",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = int(response_content["swh:deposit_id"])

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.origin_url is None  # not provided yet
    assert deposit.status == "partial"

    # one associated request to a deposit
    deposit_requests = DepositRequest.objects.filter(deposit=deposit)
    assert len(deposit_requests) == 1

    atom_entry_data = atom_dataset["entry-only-create-origin"] % (origin_url)

    for link in response_content["atom:link"]:
        if link["@rel"] == "http://purl.org/net/sword/terms/add":
            se_iri = link["@href"]
            break
    else:
        assert False, f"missing SE-IRI from {response_content['link']}"

    # when updating the first deposit post
    response = post_atom(
        authenticated_client, se_iri, data=atom_entry_data, HTTP_IN_PROGRESS="False",
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED, response.content.decode()

    response_content = parse_xml(BytesIO(response.content))
    deposit_id = int(response_content["swh:deposit_id"])

    deposit = Deposit.objects.get(pk=deposit_id)
    assert deposit.collection == deposit_collection
    assert deposit.origin_url == origin_url
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    assert len(Deposit.objects.all()) == 1

    # now 2 associated requests to a same deposit
    deposit_requests = DepositRequest.objects.filter(deposit=deposit).order_by("id")
    assert len(deposit_requests) == 2

    atom_entry_data1 = atom_dataset["entry-data1"]
    expected_meta = [
        {"metadata": parse_xml(atom_entry_data1), "raw_metadata": atom_entry_data1},
        {"metadata": parse_xml(atom_entry_data), "raw_metadata": atom_entry_data},
    ]

    for i, deposit_request in enumerate(deposit_requests):
        actual_metadata = deposit_request.metadata
        assert actual_metadata == expected_meta[i]["metadata"]
        assert deposit_request.raw_metadata == expected_meta[i]["raw_metadata"]
        assert bool(deposit_request.archive) is False


def test_replace_metadata_to_deposit_is_possible(
    tmp_path,
    authenticated_client,
    partial_deposit_with_metadata,
    deposit_collection,
    atom_dataset,
    deposit_user,
):
    """Replace all metadata with another one should return a 204 response

    """
    # given
    deposit = partial_deposit_with_metadata
    origin_url = deposit_user.provider_url + deposit.external_id
    raw_metadata0 = atom_dataset["entry-data0"] % origin_url

    requests_meta = DepositRequest.objects.filter(deposit=deposit, type="metadata")
    assert len(requests_meta) == 1
    request_meta0 = requests_meta[0]
    assert request_meta0.raw_metadata == raw_metadata0

    requests_archive0 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive0) == 1

    update_uri = reverse(EDIT_IRI, args=[deposit_collection.name, deposit.id])

    response = put_atom(
        authenticated_client, update_uri, data=atom_dataset["entry-data1"],
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


def test_add_metadata_to_deposit_is_possible(
    authenticated_client,
    deposit_collection,
    partial_deposit_with_metadata,
    atom_dataset,
    deposit_user,
):
    """Add metadata with another one should return a 204 response

    """
    deposit = partial_deposit_with_metadata
    origin_url = deposit_user.provider_url + deposit.external_id
    requests = DepositRequest.objects.filter(deposit=deposit, type="metadata")

    assert len(requests) == 1

    requests_archive0 = DepositRequest.objects.filter(deposit=deposit, type="archive")
    assert len(requests_archive0) == 1

    update_uri = reverse(SE_IRI, args=[deposit_collection.name, deposit.id])

    atom_entry = atom_dataset["entry-data1"]
    response = post_atom(authenticated_client, update_uri, data=atom_entry)

    assert response.status_code == status.HTTP_201_CREATED

    requests = DepositRequest.objects.filter(deposit=deposit, type="metadata").order_by(
        "id"
    )

    assert len(requests) == 2
    expected_raw_meta0 = atom_dataset["entry-data0"] % origin_url
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

    url = reverse(SE_IRI, args=[deposit_collection, unknown_deposit_id])
    response = post_atom(authenticated_client, url, data=atom_dataset["entry-data1"],)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_content = parse_xml(response.content)
    assert (
        "Deposit 1000 does not exist" in response_content["sword:error"]["atom:summary"]
    )


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

    url = reverse(SE_IRI, args=[unknown_collection_name, deposit.id])
    response = post_atom(authenticated_client, url, data=atom_dataset["entry-data1"],)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_content = parse_xml(response.content)
    assert "Unknown collection name" in response_content["sword:error"]["atom:summary"]


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
    url = reverse(EDIT_IRI, args=[deposit_collection.name, unknown_deposit_id])
    response = put_atom(authenticated_client, url, data=atom_dataset["entry-data1"],)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_content = parse_xml(response.content)
    assert (
        "Deposit %s does not exist" % unknown_deposit_id
        == response_content["sword:error"]["atom:summary"]
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
    response = put_atom(
        authenticated_client, update_uri, data=atom_dataset["entry-data1"],
    )
    # then
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Packaging format supported is restricted" in response.content
    for supported_format in ACCEPT_ARCHIVE_CONTENT_TYPES:
        assert supported_format.encode() in response.content


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
    deposit_swhid = CoreSWHID.from_string(complete_deposit.swhid)
    assert deposit_swhid.object_type == ObjectType.DIRECTORY
    directory_id = hash_to_bytes(deposit_swhid.object_id)

    # directory targeted by the complete_deposit does not exist in the storage
    assert list(swh_storage.directory_missing([directory_id])) == [directory_id]

    # so let's create a directory reference in the storage (current deposit targets an
    # unknown swhid)
    existing_directory = sample_data.directory
    swh_storage.directory_add([existing_directory])
    assert list(swh_storage.directory_missing([existing_directory.id])) == []

    # and patch one complete deposit swhid so it targets said reference
    complete_deposit.swhid = str(existing_directory.swhid())
    complete_deposit.save()

    actual_existing_requests_archive = DepositRequest.objects.filter(
        deposit=complete_deposit, type="archive"
    )
    nb_archives = len(actual_existing_requests_archive)
    actual_existing_requests_metadata = DepositRequest.objects.filter(
        deposit=complete_deposit, type="metadata"
    )
    nb_metadata = len(actual_existing_requests_metadata)

    update_uri = reverse(EDIT_IRI, args=[deposit_collection.name, complete_deposit.id])
    response = put_atom(
        authenticated_client,
        update_uri,
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

    directory_swhid = ExtendedSWHID.from_string(complete_deposit.swhid)
    page_results = swh_storage.raw_extrinsic_metadata_get(
        directory_swhid, metadata_authority
    )
    assert page_results == PagedResult(
        results=[
            RawExtrinsicMetadata(
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

    update_uri = reverse(EDIT_IRI, args=[deposit_collection.name, complete_deposit.id])
    response = put_atom(
        authenticated_client,
        update_uri,
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
    update_uri = reverse(EDIT_IRI, args=[deposit_collection.name, complete_deposit.id])
    response = put_atom(
        authenticated_client,
        update_uri,
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
    update_uri = reverse(EDIT_IRI, args=[deposit_collection.name, complete_deposit.id])

    atom_content = atom_dataset["entry-data-empty-body"]
    response = put_atom(
        authenticated_client,
        update_uri,
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
    update_uri = reverse(EDIT_IRI, args=[deposit_collection.name, complete_deposit.id])

    response = put_atom(
        authenticated_client,
        update_uri,
        # no title, nor author, nor name fields
        data=atom_dataset["entry-data-fail-metadata-functional-checks"],
        HTTP_X_CHECK_SWHID=complete_deposit.swhid,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert b"Functional metadata checks failure" in response.content
    # detail on the errors
    msg = (
        b"- Mandatory fields are missing ("
        b"atom:name or atom:title or codemeta:name, "
        b"atom:author or codemeta:author)"
    )
    assert msg in response.content


def test_put_atom_with_create_origin_and_external_identifier(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """<atom:external_identifier> was deprecated before <swh:create_origin>
    was introduced, clients should get an error when trying to use both

    """
    external_id = "foobar"
    origin_url = deposit_user.provider_url + external_id
    url = reverse(COL_IRI, args=[deposit_collection.name])

    response = post_atom(
        authenticated_client,
        url,
        data=atom_dataset["entry-data0"] % origin_url,
        HTTP_IN_PROGRESS="true",
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))

    for link in response_content["atom:link"]:
        if link["@rel"] == "edit":
            edit_iri = link["@href"]
            break
    else:
        assert False, response_content

    # when
    response = put_atom(
        authenticated_client,
        edit_iri,
        data=atom_dataset["error-with-external-identifier"] % external_id,
        HTTP_IN_PROGRESS="false",
    )

    assert b"&lt;external_identifier&gt; is deprecated" in response.content
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_put_atom_with_create_origin_and_reference(
    authenticated_client, deposit_collection, atom_dataset, deposit_user
):
    """<swh:reference> and <swh:create_origin> are mutually exclusive

    """
    external_id = "foobar"
    origin_url = deposit_user.provider_url + external_id
    url = reverse(COL_IRI, args=[deposit_collection.name])

    response = post_atom(
        authenticated_client,
        url,
        data=atom_dataset["entry-data0"] % origin_url,
        HTTP_IN_PROGRESS="true",
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(BytesIO(response.content))

    for link in response_content["atom:link"]:
        if link["@rel"] == "edit":
            edit_iri = link["@href"]
            break
    else:
        assert False, response_content

    # when
    response = put_atom(
        authenticated_client,
        edit_iri,
        data=atom_dataset["entry-data-with-origin-reference"].format(url=origin_url),
        HTTP_IN_PROGRESS="false",
    )

    assert b"only one may be used on a given deposit" in response.content
    assert response.status_code == status.HTTP_400_BAD_REQUEST
