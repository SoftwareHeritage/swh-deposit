# Copyright (C) 2017-2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import random

from django.urls import reverse_lazy as reverse
import pytest
from rest_framework import status

from swh.deposit.config import (
    COL_IRI,
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_PARTIAL,
    PRIVATE_GET_DEPOSIT_METADATA,
    PRIVATE_GET_UPLOAD_URLS,
    PRIVATE_PUT_DEPOSIT,
    SE_IRI,
)
from swh.deposit.loader.checker import (
    MANDATORY_ARCHIVE_INVALID,
    MANDATORY_ARCHIVE_MISSING,
    MANDATORY_ARCHIVE_UNSUPPORTED,
    DepositChecker,
)
from swh.deposit.loader.checks import METADATA_PROVENANCE_KEY, SUGGESTED_FIELDS_MISSING
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

PRIVATE_GET_DEPOSIT_METADATA_NC = PRIVATE_GET_DEPOSIT_METADATA + "-nc"
PRIVATE_PUT_DEPOSIT_NC = PRIVATE_PUT_DEPOSIT + "-nc"

BASE_URL = "https://deposit.softwareheritage.org"


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


@pytest.fixture
def deposit_checker():
    return DepositChecker()


@pytest.fixture
def datadir():
    """Override default datadir to target main test datadir"""
    return os.path.join(os.path.dirname(__file__), "../data")


@pytest.fixture
def deposited_deposit_valid_metadata(partial_deposit_with_metadata):
    partial_deposit_with_metadata.status = DEPOSIT_STATUS_DEPOSITED
    partial_deposit_with_metadata.save()
    return partial_deposit_with_metadata


@pytest.fixture()
def deposited_deposit_only_metadata(partial_deposit_only_metadata):
    partial_deposit_only_metadata.status = DEPOSIT_STATUS_DEPOSITED
    partial_deposit_only_metadata.save()
    return partial_deposit_only_metadata


def mock_http_requests(deposit, authenticated_client, requests_mock):
    """Mock HTTP requests performed by deposit checker with responses
    of django test client."""
    metadata_url = reverse(PRIVATE_GET_DEPOSIT_METADATA_NC, args=[deposit.id])
    upload_urls_url = reverse(PRIVATE_GET_UPLOAD_URLS, args=[deposit.id])
    archive_urls = authenticated_client.get(upload_urls_url).json()

    if archive_urls:
        archive_response = authenticated_client.get(archive_urls[0])
        # mock archive download
        requests_mock.get(
            archive_urls[0], content=b"".join(archive_response.streaming_content)
        )

    # mock requests to private deposit API by forwarding authenticated_client responses
    for url in (metadata_url, upload_urls_url):
        requests_mock.get(BASE_URL + url, json=authenticated_client.get(url).json())

    def status_update(request, context):
        authenticated_client.put(
            put_deposit_url, content_type="application/json", data=request.body
        )
        return None

    put_deposit_url = reverse(PRIVATE_PUT_DEPOSIT_NC, args=[deposit.id])
    requests_mock.put(
        BASE_URL + put_deposit_url,
        content=status_update,
    )


def test_checker_deposit_missing_metadata(
    deposit_checker,
    deposited_deposit,
    authenticated_client,
    requests_mock,
):
    mock_http_requests(deposited_deposit, authenticated_client, requests_mock)
    actual_result = deposit_checker.check(
        collection="test", deposit_id=deposited_deposit.id
    )
    assert actual_result == {
        "status": "failed",
        "status_detail": {"metadata": [{"summary": "Missing Atom document"}]},
    }


def test_checker_deposit_valid_metadata(
    deposit_checker,
    deposited_deposit_valid_metadata,
    authenticated_client,
    requests_mock,
):
    mock_http_requests(
        deposited_deposit_valid_metadata,
        authenticated_client,
        requests_mock,
    )
    actual_result = deposit_checker.check(
        collection="test", deposit_id=deposited_deposit_valid_metadata.id
    )
    assert actual_result == {
        "status": "eventful",
        "status_detail": {
            "metadata": [
                {
                    "fields": [METADATA_PROVENANCE_KEY],
                    "summary": SUGGESTED_FIELDS_MISSING,
                },
            ]
        },
    }


def test_checker_deposit_only_metadata(
    deposit_checker,
    deposited_deposit_only_metadata,
    authenticated_client,
    requests_mock,
):
    mock_http_requests(
        deposited_deposit_only_metadata,
        authenticated_client,
        requests_mock,
    )
    actual_result = deposit_checker.check(
        collection="test", deposit_id=deposited_deposit_only_metadata.id
    )

    assert actual_result == {
        "status": "failed",
        "status_detail": {
            "archive": [{"summary": MANDATORY_ARCHIVE_MISSING}],
            "metadata": [
                {
                    "summary": SUGGESTED_FIELDS_MISSING,
                    "fields": [METADATA_PROVENANCE_KEY],
                }
            ],
        },
    }


def test_checker_deposit_exception_raised(
    deposit_checker,
    deposited_deposit_valid_metadata,
    authenticated_client,
    requests_mock,
    mocker,
):
    mock_http_requests(
        deposited_deposit_valid_metadata,
        authenticated_client,
        requests_mock,
    )
    mocker.patch("swh.deposit.loader.checker.check_metadata").side_effect = ValueError(
        "Error when checking metadata"
    )
    actual_result = deposit_checker.check(
        collection="test", deposit_id=deposited_deposit_valid_metadata.id
    )
    assert actual_result == {
        "status": "failed",
        "status_detail": {
            "exception": "ValueError: Error when checking metadata",
        },
    }


def test_checker_deposit_invalid_archive(
    deposit_checker,
    ready_deposit_invalid_archive,
    authenticated_client,
    requests_mock,
):
    mock_http_requests(
        ready_deposit_invalid_archive,
        authenticated_client,
        requests_mock,
    )

    actual_result = deposit_checker.check(
        collection="test", deposit_id=ready_deposit_invalid_archive.id
    )

    assert actual_result == {
        "status": "failed",
        "status_detail": {
            "archive": [{"summary": MANDATORY_ARCHIVE_UNSUPPORTED}],
            "metadata": [{"summary": "Missing Atom document"}],
        },
    }


@pytest.mark.parametrize("extension", ["zip", "tar", "tar.gz", "tar.bz2", "tar.xz"])
def test_deposit_ok(
    tmp_path,
    authenticated_client,
    deposit_collection,
    extension,
    atom_dataset,
    deposit_checker,
    requests_mock,
):
    """Proper deposit should succeed the checks (-> status ready)"""
    deposit = create_deposit_with_archive(
        tmp_path, extension, authenticated_client, deposit_collection.name, atom_dataset
    )

    mock_http_requests(
        deposit,
        authenticated_client,
        requests_mock,
    )

    actual_result = deposit_checker.check(collection="test", deposit_id=deposit.id)

    assert actual_result == {
        "status": "eventful",
        "status_detail": {
            "metadata": [
                {
                    "summary": SUGGESTED_FIELDS_MISSING,
                    "fields": [METADATA_PROVENANCE_KEY],
                }
            ]
        },
    }


@pytest.mark.parametrize("extension", ["zip", "tar", "tar.gz", "tar.bz2", "tar.xz"])
def test_deposit_invalid_tarball(
    tmp_path,
    authenticated_client,
    deposit_collection,
    extension,
    atom_dataset,
    requests_mock,
    deposit_checker,
):
    """Deposit with tarball (of 1 tarball) should fail the checks: rejected"""
    deposit = create_deposit_archive_with_archive(
        tmp_path, extension, authenticated_client, deposit_collection.name, atom_dataset
    )

    mock_http_requests(
        deposit,
        authenticated_client,
        requests_mock,
    )

    actual_result = deposit_checker.check(collection="test", deposit_id=deposit.id)

    assert actual_result == {
        "status": "failed",
        "status_detail": {
            "archive": [{"summary": MANDATORY_ARCHIVE_INVALID}],
            "metadata": [
                {
                    "summary": SUGGESTED_FIELDS_MISSING,
                    "fields": [METADATA_PROVENANCE_KEY],
                }
            ],
        },
    }


def test_deposit_ko_missing_tarball(
    authenticated_client,
    ready_deposit_only_metadata,
    requests_mock,
    deposit_checker,
):
    """Deposit without archive should fail the checks: rejected"""
    deposit = ready_deposit_only_metadata
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    mock_http_requests(
        deposit,
        authenticated_client,
        requests_mock,
    )

    actual_result = deposit_checker.check(collection="test", deposit_id=deposit.id)

    assert actual_result == {
        "status": "failed",
        "status_detail": {
            "archive": [{"summary": MANDATORY_ARCHIVE_MISSING}],
            "metadata": [
                {
                    "summary": SUGGESTED_FIELDS_MISSING,
                    "fields": [METADATA_PROVENANCE_KEY],
                }
            ],
        },
    }


def test_deposit_ko_unsupported_tarball(
    authenticated_client,
    ready_deposit_invalid_archive,
    requests_mock,
    deposit_checker,
):
    """Deposit with unsupported tarball should fail checks and be rejected"""
    deposit = ready_deposit_invalid_archive
    assert DEPOSIT_STATUS_DEPOSITED == deposit.status

    mock_http_requests(
        deposit,
        authenticated_client,
        requests_mock,
    )

    actual_result = deposit_checker.check(collection="test", deposit_id=deposit.id)

    assert actual_result == {
        "status": "failed",
        "status_detail": {
            "archive": [{"summary": MANDATORY_ARCHIVE_UNSUPPORTED}],
            "metadata": [{"summary": "Missing Atom document"}],
        },
    }


def test_deposit_ko_unsupported_tarball_prebasic_check(
    tmp_path,
    authenticated_client,
    deposit_collection,
    atom_dataset,
    requests_mock,
    deposit_checker,
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

    mock_http_requests(
        deposit,
        authenticated_client,
        requests_mock,
    )

    actual_result = deposit_checker.check(collection="test", deposit_id=deposit.id)

    assert actual_result == {
        "status": "failed",
        "status_detail": {
            "archive": [{"summary": MANDATORY_ARCHIVE_UNSUPPORTED}],
            "metadata": [
                {
                    "summary": SUGGESTED_FIELDS_MISSING,
                    "fields": [METADATA_PROVENANCE_KEY],
                }
            ],
        },
    }


def test_check_deposit_metadata_ok(
    authenticated_client,
    ready_deposit_ok,
    requests_mock,
    deposit_checker,
):
    """Proper deposit should succeed the checks (-> status ready)
    with all **MUST** metadata

    using the codemeta metadata test set
    """
    deposit = ready_deposit_ok
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED

    mock_http_requests(
        deposit,
        authenticated_client,
        requests_mock,
    )

    actual_result = deposit_checker.check(collection="test", deposit_id=deposit.id)

    assert actual_result == {
        "status": "eventful",
        "status_detail": {
            "metadata": [
                {
                    "summary": SUGGESTED_FIELDS_MISSING,
                    "fields": [METADATA_PROVENANCE_KEY],
                }
            ]
        },
    }
