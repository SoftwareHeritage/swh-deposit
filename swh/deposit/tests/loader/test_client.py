# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import json
import pytest
import unittest

from typing import Any, Callable, Optional
from urllib.parse import urlparse

from swh.deposit.client import PrivateApiDepositClient
from swh.deposit.config import DEPOSIT_STATUS_LOAD_SUCCESS, DEPOSIT_STATUS_LOAD_FAILURE


CLIENT_TEST_CONFIG = {
    "url": "https://nowhere.org/",
    "auth": {},  # no authentication in test scenario
}


def build_expected_path(datadir, base_url: str, api_url: str) -> str:
    """Build expected path from api to served file

    """
    url = urlparse(base_url)
    dirname = "%s_%s" % (url.scheme, url.hostname)
    if api_url.endswith("/"):
        api_url = api_url[:-1]
    if api_url.startswith("/"):
        api_url = api_url[1:]
    suffix_path = api_url.replace("/", "_")
    return os.path.join(datadir, dirname, suffix_path)


def test_build_expected_path(datadir):
    actual_path = build_expected_path(datadir, "http://example.org", "/hello/you/")

    assert actual_path == os.path.join(datadir, "http_example.org", "hello_you")


def read_served_path(
    datadir,
    base_url: str,
    api_url: str,
    convert_fn: Optional[Callable[[str], Any]] = None,
) -> bytes:
    """Read served path

    """
    archive_path = build_expected_path(datadir, base_url, api_url)
    with open(archive_path, "rb") as f:
        content = f.read()
    if convert_fn:
        content = convert_fn(content.decode("utf-8"))
    return content


def test_read_served_path(datadir):
    actual_content = read_served_path(datadir, "http://example.org", "/hello/you/")

    assert actual_content == b"hello people\n"

    actual_content2 = read_served_path(
        datadir, "http://example.org", "/hello.json", convert_fn=json.loads
    )

    assert actual_content2 == {"a": [1, 3]}


# private api to retrieve archive


def test_archive_get(tmp_path, datadir, requests_mock_datadir):
    """Retrieving archive data through private api should stream data

    """
    api_url = "/1/private/test/1/raw/"
    client = PrivateApiDepositClient(config=CLIENT_TEST_CONFIG)

    expected_content = read_served_path(datadir, client.base_url, api_url)

    archive_path = os.path.join(tmp_path, "test.archive")
    archive_path = client.archive_get(api_url, archive_path)

    assert os.path.exists(archive_path) is True

    with open(archive_path, "rb") as f:
        actual_content = f.read()

    assert actual_content == expected_content
    assert client.base_url == CLIENT_TEST_CONFIG["url"]
    assert client.auth is None


def test_archive_get_auth(tmp_path, datadir, requests_mock_datadir):
    """Retrieving archive data through private api should stream data

    """
    api_url = "/1/private/test/1/raw/"
    config = CLIENT_TEST_CONFIG.copy()
    config["auth"] = {  # add authentication setup
        "username": "user",
        "password": "pass",
    }
    client = PrivateApiDepositClient(config)

    expected_content = read_served_path(datadir, client.base_url, api_url)

    archive_path = os.path.join(tmp_path, "test.archive")
    archive_path = client.archive_get(api_url, archive_path)

    assert os.path.exists(archive_path) is True

    with open(archive_path, "rb") as f:
        actual_content = f.read()

    assert actual_content == expected_content
    assert client.base_url == CLIENT_TEST_CONFIG["url"]
    assert client.auth == ("user", "pass")


def test_archive_get_ko(tmp_path, datadir, requests_mock_datadir):
    """Reading archive can fail for some reasons

    """
    unknown_api_url = "/1/private/unknown/deposit-id/raw/"
    client = PrivateApiDepositClient(config=CLIENT_TEST_CONFIG)

    with pytest.raises(ValueError, match="Problem when retrieving deposit"):
        client.archive_get(unknown_api_url, "some/path")


# private api read metadata


def test_metadata_get(datadir, requests_mock_datadir):
    """Reading archive should write data in temporary directory

    """
    api_url = "/1/private/test/1/metadata"
    client = PrivateApiDepositClient(config=CLIENT_TEST_CONFIG)
    actual_metadata = client.metadata_get(api_url)

    assert isinstance(actual_metadata, str) is False
    expected_content = read_served_path(
        datadir, client.base_url, api_url, convert_fn=json.loads
    )
    assert actual_metadata == expected_content


def test_metadata_get_ko(requests_mock_datadir):
    """Reading metadata can fail for some reasons

    """
    unknown_api_url = "/1/private/unknown/deposit-id/metadata/"
    client = PrivateApiDepositClient(config=CLIENT_TEST_CONFIG)

    with pytest.raises(ValueError, match="Problem when retrieving metadata"):
        client.metadata_get(unknown_api_url)


# private api check


def test_check(requests_mock_datadir):
    """When check ok, this should return the deposit's status

    """
    api_url = "/1/private/test/1/check"
    client = PrivateApiDepositClient(config=CLIENT_TEST_CONFIG)

    r = client.check(api_url)
    assert r == "something"


def test_check_fails(requests_mock_datadir):
    """Checking deposit can fail for some reason

    """
    unknown_api_url = "/1/private/test/10/check"
    client = PrivateApiDepositClient(config=CLIENT_TEST_CONFIG)

    with pytest.raises(ValueError, match="Problem when checking deposit"):
        client.check(unknown_api_url)


# private api update status


class FakeRequestClientPut:
    """Fake Request client dedicated to put request method calls.

    """

    args = None
    kwargs = None

    def put(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class PrivateApiDepositClientStatusUpdateTest(unittest.TestCase):
    def test_status_update(self):
        """Update status

        """
        _client = FakeRequestClientPut()
        deposit_client = PrivateApiDepositClient(
            config=CLIENT_TEST_CONFIG, _client=_client
        )

        deposit_client.status_update(
            "/update/status",
            DEPOSIT_STATUS_LOAD_SUCCESS,
            revision_id="some-revision-id",
        )

        self.assertEqual(_client.args, ("https://nowhere.org/update/status",))
        self.assertEqual(
            _client.kwargs,
            {
                "json": {
                    "status": DEPOSIT_STATUS_LOAD_SUCCESS,
                    "revision_id": "some-revision-id",
                }
            },
        )

    def test_status_update_with_no_revision_id(self):
        """Reading metadata can fail for some reasons

        """
        _client = FakeRequestClientPut()
        deposit_client = PrivateApiDepositClient(
            config=CLIENT_TEST_CONFIG, _client=_client
        )

        deposit_client.status_update("/update/status/fail", DEPOSIT_STATUS_LOAD_FAILURE)

        self.assertEqual(_client.args, ("https://nowhere.org/update/status/fail",))
        self.assertEqual(
            _client.kwargs, {"json": {"status": DEPOSIT_STATUS_LOAD_FAILURE,}}
        )
