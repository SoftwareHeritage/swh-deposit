# Copyright (C) 2017-2023  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from os.path import exists, join
import tarfile

from django.urls import reverse_lazy as reverse
from rest_framework import status

from swh.deposit.api.private.deposit_read import aggregate_tarballs
from swh.deposit.config import EM_IRI, PRIVATE_GET_RAW_CONTENT
from swh.deposit.models import DepositRequest
from swh.deposit.tests.common import (
    compute_info,
    create_arborescence_archive,
    post_archive,
)

PRIVATE_GET_RAW_CONTENT_NC = PRIVATE_GET_RAW_CONTENT + "-nc"


def private_get_raw_url_endpoints(collection, deposit):
    """There are 2 endpoints to check (one with collection, one without)"""
    return [
        reverse(PRIVATE_GET_RAW_CONTENT, args=[collection.name, deposit.id]),
        reverse(PRIVATE_GET_RAW_CONTENT_NC, args=[deposit.id]),
    ]


def test_access_to_existing_deposit_with_one_archive(
    authenticated_client,
    deposit_collection,
    complete_deposit,
    sample_archive,
    tmp_path,
):
    """Access to deposit should stream a 200 response with its raw content"""
    deposit = complete_deposit

    for i, url in enumerate(private_get_raw_url_endpoints(deposit_collection, deposit)):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response["content-type"] == "application/tar"

        # write the response stream in a temporary archive
        archive_path = join(tmp_path, f"archive_{i}.tar")
        with open(archive_path, "wb") as f:
            for chunk in response.streaming_content:
                f.write(chunk)

        # to check its properties are correct
        tfile = tarfile.open(archive_path)
        assert set(tfile.getnames()) == {".", "./file1"}
        assert tfile.extractfile("./file1").read() == b"some content in file"


def test_access_to_existing_deposit_with_multiple_archives(
    tmp_path, authenticated_client, deposit_collection, partial_deposit, sample_archive
):
    """Access to deposit should stream a 200 response with its raw contents"""
    deposit = partial_deposit
    archive2 = create_arborescence_archive(
        tmp_path, "archive2", "file2", b"some other content in file"
    )

    # Add a second archive to deposit
    update_uri = reverse(EM_IRI, args=[deposit_collection.name, deposit.id])
    response = authenticated_client.post(
        update_uri,
        content_type="application/zip",  # as zip
        data=archive2["data"],
        # + headers
        CONTENT_LENGTH=archive2["length"],
        HTTP_SLUG=deposit.external_id,
        HTTP_CONTENT_MD5=archive2["md5sum"],
        HTTP_PACKAGING="http://purl.org/net/sword/package/SimpleZip",
        HTTP_IN_PROGRESS="false",
        HTTP_CONTENT_DISPOSITION="attachment; filename=%s" % (archive2["name"],),
    )
    assert response.status_code == status.HTTP_201_CREATED

    for i, url in enumerate(private_get_raw_url_endpoints(deposit_collection, deposit)):
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response["content-type"] == "application/tar"
        # write the response stream in a temporary archive
        archive_path = join(tmp_path, f"archive_{i}.tar")
        with open(archive_path, "wb") as f:
            for chunk in response.streaming_content:
                f.write(chunk)

        # to check its properties are correct
        tfile = tarfile.open(archive_path)
        assert set(tfile.getnames()) == {".", "./file1", "./file2"}
        assert tfile.extractfile("./file1").read() == b"some content in file"
        assert tfile.extractfile("./file2").read() == b"some other content in file"


def test_aggregate_tarballs_with_strange_archive(
    datadir, authenticated_client, tmp_path, partial_deposit
):
    deposit = partial_deposit
    update_uri = reverse(EM_IRI, args=[deposit.collection.name, deposit.id])
    archive = compute_info(join(datadir, "archives", "single-artifact-package.tar.gz"))

    response = post_archive(
        authenticated_client,
        update_uri,
        archive,
        content_type="application/x-tar",
        in_progress=False,
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    deposit_requests = DepositRequest.objects.filter(type="archive", deposit=deposit)

    archives = [dr.archive for dr in deposit_requests]

    with aggregate_tarballs(tmp_path, archives) as tarball_path:
        assert exists(tarball_path)


def test_aggregate_tarballs_with_remote_tarball(
    datadir, authenticated_client, tmp_path, partial_deposit
):
    """Tarballs can be stored remotely and still be accessible for reading."""
    deposit = partial_deposit
    update_uri = reverse(EM_IRI, args=[deposit.collection.name, deposit.id])
    archive = compute_info(join(datadir, "archives", "single-artifact-package.tar.gz"))

    response = post_archive(
        authenticated_client,
        update_uri,
        archive,
        content_type="application/x-tar",
        in_progress=False,
    )

    # then
    assert response.status_code == status.HTTP_201_CREATED

    deposit_requests = DepositRequest.objects.filter(type="archive", deposit=deposit)

    all_archives = [dr.archive for dr in deposit_requests]

    archives = [a for a in all_archives if not a.name.endswith(archive["name"])]

    # We'll patch the behavior of this archive to be read as if it were a remote one
    interesting_archive = [a for a in all_archives if a.name.endswith(archive["name"])][
        0
    ]

    class RemoteTarball:
        """Basic remote tarball implementation for test purposes."""

        name = archive["name"]

        @property
        def path(self):
            raise NotImplementedError("We fake the path implementation")

        open = interesting_archive.open

    archives.append(RemoteTarball())

    with aggregate_tarballs(tmp_path, archives) as tarball_path:
        assert exists(tarball_path)
