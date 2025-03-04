# Copyright (C) 2025  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from hashlib import sha1
import os
import secrets
import shutil
import subprocess

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient
from django.urls import reverse_lazy as reverse
import pytest
import requests
from rest_framework import status

from swh.deposit.config import DEPOSIT_STATUS_PARTIAL, EM_IRI, PRIVATE_GET_UPLOAD_URLS
from swh.deposit.tests.common import create_arborescence_archive
from swh.deposit.tests.conftest import create_deposit

AZURITE_EXE = shutil.which(
    "azurite-blob", path=os.environ.get("AZURITE_PATH", os.environ.get("PATH"))
)


@pytest.fixture(scope="module")
def azure_container_name():
    return secrets.token_hex(10)


@pytest.fixture(scope="module")
def azurite_connection_string(tmpdir_factory):
    host = "127.0.0.1"

    azurite_path = tmpdir_factory.mktemp("azurite")

    azurite_proc = subprocess.Popen(
        [
            AZURITE_EXE,
            "--blobHost",
            host,
            "--blobPort",
            "0",
        ],
        stdout=subprocess.PIPE,
        cwd=azurite_path,
    )

    prefix = b"Azurite Blob service successfully listens on "
    for line in azurite_proc.stdout:
        if line.startswith(prefix):
            base_url = line[len(prefix) :].decode().strip()
            break
    else:
        assert False, "Did not get Azurite Blob service port."

    # https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite#well-known-storage-account-and-key
    account_name = "devstoreaccount1"
    account_key = (
        "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq"
        "/K1SZFPTOtr/KBHBeksoGMGw=="
    )

    container_url = f"{base_url}/{account_name}"

    # unset proxy set by the swh_proxy session fixture
    del os.environ["http_proxy"]
    del os.environ["https_proxy"]

    yield (
        f"DefaultEndpointsProtocol=https;"
        f"AccountName={account_name};"
        f"AccountKey={account_key};"
        f"BlobEndpoint={container_url};"
    )

    # reset proxy
    os.environ["http_proxy"] = "http://localhost:999"
    os.environ["https_proxy"] = "http://localhost:999"

    azurite_proc.kill()
    azurite_proc.wait(2)


@pytest.fixture(
    params=["sample_archive", "sample_tarfile", "sample_tarfile_tgz_extension"]
)
def sample_tarball(request):
    return request.getfixturevalue(request.param)


def check_deposit_upload_urls(
    tmp_path,
    authenticated_client,
    deposit_collection,
    sample_tarball,
):
    # Add a first archive to deposit
    partial_deposit = create_deposit(
        authenticated_client,
        collection_name=deposit_collection.name,
        sample_archive=sample_tarball,
        external_id="external-id",
        deposit_status=DEPOSIT_STATUS_PARTIAL,
    )

    # Add a second archive to deposit
    archive2 = create_arborescence_archive(
        tmp_path, "archive2", "file2", b"some other content in file"
    )
    update_uri = reverse(EM_IRI, args=[deposit_collection.name, partial_deposit.id])
    response = authenticated_client.post(
        update_uri,
        content_type="application/zip",  # as zip
        data=archive2["data"],
        # + headers
        CONTENT_LENGTH=archive2["length"],
        HTTP_SLUG=partial_deposit.external_id,
        HTTP_CONTENT_MD5=archive2["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=%s" % (archive2["name"],),
    )
    assert response.status_code == status.HTTP_201_CREATED

    # check uploaded tarballs can be downloaded using URLs and
    # compare download contents with originals
    url = reverse(PRIVATE_GET_UPLOAD_URLS, args=[partial_deposit.id])
    response = authenticated_client.get(url)
    upload_urls = response.json()
    assert len(upload_urls) == 2
    assert sample_tarball["name"] in upload_urls[0]
    assert "archive2.zip" in upload_urls[1]
    tarball_shasums = set()
    for upload_url in upload_urls:
        response = (
            # when storage backend is local filesystem and served by django
            authenticated_client.get(upload_url)
            if upload_url.startswith("http://testserver/")
            # when storage backend is azurite
            else requests.get(upload_url)
        )
        assert response.status_code == status.HTTP_200_OK
        tarball_shasums.add(
            sha1(
                b"".join(response.streaming_content)
                if hasattr(response, "streaming_content")
                else response.content
            ).hexdigest()
        )

    assert tarball_shasums == {sample_tarball["sha1sum"], archive2["sha1sum"]}


def test_deposit_upload_urls_local_filesystem_storage_backend(
    tmp_path,
    authenticated_client,
    deposit_collection,
    sample_tarball,
):
    check_deposit_upload_urls(
        tmp_path,
        authenticated_client,
        deposit_collection,
        sample_tarball,
    )


@pytest.mark.skipif(not AZURITE_EXE, reason="azurite not found in AZURITE_PATH or PATH")
def test_deposit_upload_urls_azure_storage_backend(
    tmp_path,
    authenticated_client,
    deposit_collection,
    sample_tarball,
    settings,
    azurite_connection_string,
    azure_container_name,
):
    blob_client = BlobServiceClient.from_connection_string(azurite_connection_string)
    try:
        blob_client.create_container(azure_container_name)
    except ResourceExistsError:
        pass

    settings.STORAGES = {
        "default": {
            "BACKEND": "storages.backends.azure_storage.AzureStorage",
            "OPTIONS": {
                "connection_string": azurite_connection_string,
                "azure_container": azure_container_name,
                "expiration_secs": 1800,
                "object_parameters": {
                    "content_encoding": None,
                },
            },
        },
    }
    check_deposit_upload_urls(
        tmp_path,
        authenticated_client,
        deposit_collection,
        sample_tarball,
    )
