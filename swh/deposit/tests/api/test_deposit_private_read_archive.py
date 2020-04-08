# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import io
import zipfile

from django.urls import reverse
from rest_framework import status

from swh.deposit.config import PRIVATE_GET_RAW_CONTENT, EM_IRI
from swh.deposit.tests.common import create_arborescence_archive


PRIVATE_GET_RAW_CONTENT_NC = PRIVATE_GET_RAW_CONTENT + "-nc"


def private_get_raw_url_endpoints(collection, deposit):
    """There are 2 endpoints to check (one with collection, one without)"""
    return [
        reverse(PRIVATE_GET_RAW_CONTENT, args=[collection.name, deposit.id]),
        reverse(PRIVATE_GET_RAW_CONTENT_NC, args=[deposit.id]),
    ]


def test_access_to_existing_deposit_with_one_archive(
    authenticated_client, deposit_collection, complete_deposit, sample_archive
):
    """Access to deposit should stream a 200 response with its raw content

    """
    deposit = complete_deposit

    for url in private_get_raw_url_endpoints(deposit_collection, deposit):
        r = authenticated_client.get(url)

        assert r.status_code == status.HTTP_200_OK
        assert r._headers["content-type"][1] == "application/zip"

        # read the stream
        data = b"".join(r.streaming_content)
        # extract the file from the zip
        zfile = zipfile.ZipFile(io.BytesIO(data))
        assert zfile.namelist() == ["file1"]
        assert zfile.open("file1").read() == b"some content in file"


def test_access_to_existing_deposit_with_multiple_archives(
    tmp_path, authenticated_client, deposit_collection, partial_deposit, sample_archive
):
    """Access to deposit should stream a 200 response with its raw contents

    """
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

    for url in private_get_raw_url_endpoints(deposit_collection, deposit):
        r = authenticated_client.get(url)

        assert r.status_code == status.HTTP_200_OK
        assert r._headers["content-type"][1] == "application/zip"
        # read the stream
        data = b"".join(r.streaming_content)
        # extract the file from the zip
        zfile = zipfile.ZipFile(io.BytesIO(data))
        assert set(zfile.namelist()) == {"file1", "file2"}
        assert zfile.open("file1").read() == b"some content in file"
        assert zfile.open("file2").read() == b"some other content in file"
