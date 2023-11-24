# Copyright (C) 2017-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import random

from django.urls import reverse_lazy as reverse
import pytest
from rest_framework import status

from swh.deposit.api.checks import METADATA_PROVENANCE_KEY, SUGGESTED_FIELDS_MISSING
from swh.deposit.api.private.deposit_check import (
    MANDATORY_ARCHIVE_INVALID,
    MANDATORY_ARCHIVE_MISSING,
    MANDATORY_ARCHIVE_UNSUPPORTED,
)
from swh.deposit.config import (
    COL_IRI,
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_PARTIAL,
    DEPOSIT_STATUS_REJECTED,
    DEPOSIT_STATUS_VERIFIED,
    PRIVATE_CHECK_DEPOSIT,
    SE_IRI,
)
from swh.deposit.models import Deposit
from swh.deposit.parsers import parse_xml
from swh.deposit.tests.common import (
    SUPPORTED_TARBALL_MODES,
    create_arborescence_archive,
    create_archive_with_archive,
    post_archive,
    post_atom,
)
from swh.deposit.utils import NAMESPACES

PRIVATE_CHECK_DEPOSIT_NC = PRIVATE_CHECK_DEPOSIT + "-nc"


def private_check_url_endpoints(collection, deposit):
    """There are 2 endpoints to check (one with collection, one without)"""
    return [
        reverse(PRIVATE_CHECK_DEPOSIT, args=[collection.name, deposit.id]),
        reverse(PRIVATE_CHECK_DEPOSIT_NC, args=[deposit.id]),
    ]


@pytest.mark.parametrize("extension", ["zip", "tar", "tar.gz", "tar.bz2", "tar.xz"])
def test_deposit_ok(
    tmp_path, authenticated_client, deposit_collection, extension, atom_dataset
):
    """Proper deposit should succeed the checks (-> status ready)"""
    deposit = create_deposit_with_archive(
        tmp_path, extension, authenticated_client, deposit_collection.name, atom_dataset
    )

    for url in private_check_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == DEPOSIT_STATUS_VERIFIED, data
        deposit = Deposit.objects.get(pk=deposit.id)
        assert deposit.status == DEPOSIT_STATUS_VERIFIED

        # Deposit is ok but it's missing suggested fields in its metadata detected by
        # the checks
        status_detail = deposit.status_detail["metadata"]
        assert len(status_detail) == 1
        suggested = status_detail[0]
        assert suggested["summary"] == SUGGESTED_FIELDS_MISSING
        assert set(suggested["fields"]) == set([METADATA_PROVENANCE_KEY])

        deposit.status = DEPOSIT_STATUS_DEPOSITED
        deposit.save()


@pytest.mark.parametrize("extension", ["zip", "tar", "tar.gz", "tar.bz2", "tar.xz"])
def test_deposit_invalid_tarball(
    tmp_path, authenticated_client, deposit_collection, extension, atom_dataset
):
    """Deposit with tarball (of 1 tarball) should fail the checks: rejected"""
    deposit = create_deposit_archive_with_archive(
        tmp_path, extension, authenticated_client, deposit_collection.name, atom_dataset
    )
    for url in private_check_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == DEPOSIT_STATUS_REJECTED
        details = data["details"]
        # archive checks failure
        assert len(details["archive"]) == 1
        assert details["archive"][0]["summary"] == MANDATORY_ARCHIVE_INVALID

        deposit = Deposit.objects.get(pk=deposit.id)
        assert deposit.status == DEPOSIT_STATUS_REJECTED


def test_deposit_ko_missing_tarball(
    authenticated_client, deposit_collection, ready_deposit_only_metadata
):
    """Deposit without archive should fail the checks: rejected"""
    deposit = ready_deposit_only_metadata
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    for url in private_check_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == DEPOSIT_STATUS_REJECTED
        details = data["details"]
        # archive checks failure
        assert len(details["archive"]) == 1
        assert details["archive"][0]["summary"] == MANDATORY_ARCHIVE_MISSING
        deposit = Deposit.objects.get(pk=deposit.id)
        assert deposit.status == DEPOSIT_STATUS_REJECTED

        deposit.status = DEPOSIT_STATUS_DEPOSITED
        deposit.save()


def test_deposit_ko_unsupported_tarball(
    tmp_path, authenticated_client, deposit_collection, ready_deposit_invalid_archive
):
    """Deposit with unsupported tarball should fail checks and be rejected"""
    deposit = ready_deposit_invalid_archive
    assert DEPOSIT_STATUS_DEPOSITED == deposit.status

    for url in private_check_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == DEPOSIT_STATUS_REJECTED
        details = data["details"]

        # archive checks failure
        assert len(details["archive"]) == 1
        assert details["archive"][0]["summary"] == MANDATORY_ARCHIVE_UNSUPPORTED
        # metadata check failure
        assert len(details["metadata"]) == 1
        mandatory = details["metadata"][0]
        assert mandatory["summary"] == "Missing Atom document"

        deposit = Deposit.objects.get(pk=deposit.id)
        assert deposit.status == DEPOSIT_STATUS_REJECTED

        deposit.status = DEPOSIT_STATUS_DEPOSITED
        deposit.save()


def test_deposit_ko_unsupported_tarball_prebasic_check(
    tmp_path, authenticated_client, deposit_collection, atom_dataset
):
    """Deposit with unsupported tarball extension should fail checks and be rejected"""

    invalid_gz_mode = random.choice(
        [f"{ext}-foobar" for ext in SUPPORTED_TARBALL_MODES]
    )
    invalid_extension = f"tar.{invalid_gz_mode}"

    deposit = create_deposit_with_archive(
        tmp_path,
        invalid_extension,
        authenticated_client,
        deposit_collection.name,
        atom_dataset,
    )
    assert DEPOSIT_STATUS_DEPOSITED == deposit.status
    for url in private_check_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == DEPOSIT_STATUS_REJECTED
        details = data["details"]
        # archive checks failure
        assert len(details["archive"]) == 1
        assert details["archive"][0]["summary"] == MANDATORY_ARCHIVE_UNSUPPORTED

        deposit = Deposit.objects.get(pk=deposit.id)
        assert deposit.status == DEPOSIT_STATUS_REJECTED


def test_check_deposit_metadata_ok(
    authenticated_client, deposit_collection, ready_deposit_ok
):
    """Proper deposit should succeed the checks (-> status ready)
    with all **MUST** metadata

    using the codemeta metadata test set
    """
    deposit = ready_deposit_ok
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    for url in private_check_url_endpoints(deposit_collection, deposit):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == DEPOSIT_STATUS_VERIFIED, data
        deposit = Deposit.objects.get(pk=deposit.id)
        assert deposit.status == DEPOSIT_STATUS_VERIFIED

        deposit.status = DEPOSIT_STATUS_DEPOSITED
        deposit.save()


def create_deposit(archive, client, collection_name, atom_dataset):
    """Create a deposit with archive (and metadata) for client in the collection name."""
    # we deposit it
    response = post_archive(
        client,
        reverse(COL_IRI, args=[collection_name]),
        archive,
        content_type="application/x-tar",
        slug="external-id",
        in_progress=True,
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(response.content)
    deposit_status = response_content.findtext(
        "swh:deposit_status", namespaces=NAMESPACES
    )
    assert deposit_status == DEPOSIT_STATUS_PARTIAL
    deposit_id = int(response_content.findtext("swh:deposit_id", namespaces=NAMESPACES))

    origin_url = client.deposit_client.provider_url
    response = post_atom(
        client,
        reverse(SE_IRI, args=[collection_name, deposit_id]),
        data=atom_dataset["entry-data0"] % origin_url,
        in_progress=False,
    )

    assert response.status_code == status.HTTP_201_CREATED
    response_content = parse_xml(response.content)
    deposit_status = response_content.findtext(
        "swh:deposit_status", namespaces=NAMESPACES
    )
    assert deposit_status == DEPOSIT_STATUS_DEPOSITED

    deposit = Deposit.objects.get(pk=deposit_id)
    assert DEPOSIT_STATUS_DEPOSITED == deposit.status
    return deposit


def create_deposit_with_archive(
    root_path, archive_extension, client, collection_name, atom_dataset
):
    """Create a deposit with a valid archive."""
    # we create the holding archive to a given extension
    archive = create_arborescence_archive(
        root_path,
        "archive1",
        "file1",
        b"some content in file",
        extension=archive_extension,
    )

    return create_deposit(archive, client, collection_name, atom_dataset)


def create_deposit_archive_with_archive(
    root_path, archive_extension, client, collection_name, atom_dataset
):
    """Create a deposit with an invalid archive (archive within archive)"""

    # we create the holding archive to a given extension
    archive = create_arborescence_archive(
        root_path,
        "archive1",
        "file1",
        b"some content in file",
        extension=archive_extension,
    )

    # now we create an archive holding the first created archive
    invalid_archive = create_archive_with_archive(root_path, "invalid.tgz", archive)

    return create_deposit(invalid_archive, client, collection_name, atom_dataset)
