# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import contextlib
import logging
import os
import re
from unittest.mock import MagicMock

from click.testing import CliRunner
import pytest

from swh.deposit.client import PublicApiDepositClient, MaintenanceError
from swh.deposit.cli.client import generate_slug, _url, _client, _collection, InputError
from swh.deposit.cli import deposit as cli
from ..conftest import TEST_USER


EXAMPLE_SERVICE_DOCUMENT = {
    "service": {"workspace": {"collection": {"sword:name": "softcol",}}}
}


@pytest.fixture
def slug():
    return generate_slug()


@pytest.fixture
def client_mock(mocker, slug):
    """A successful deposit client with hard-coded default values

    """
    mocker.patch("swh.deposit.cli.client.generate_slug", return_value=slug)
    mock_client = MagicMock()
    mocker.patch("swh.deposit.cli.client._client", return_value=mock_client)
    mock_client.service_document.return_value = EXAMPLE_SERVICE_DOCUMENT
    mock_client.deposit_create.return_value = '{"foo": "bar"}'
    return mock_client


@pytest.fixture
def client_mock_api_down(mocker, slug):
    """A mock client whose connection with api fails due to maintenance issue

    """
    mocker.patch("swh.deposit.cli.client.generate_slug", return_value=slug)
    mock_client = MagicMock()
    mocker.patch("swh.deposit.cli.client._client", return_value=mock_client)
    mock_client.service_document.side_effect = MaintenanceError(
        "Database backend maintenance: Temporarily unavailable, try again later."
    )
    return mock_client


def test_url():
    assert _url("http://deposit") == "http://deposit/1"
    assert _url("https://other/1") == "https://other/1"


def test_client():
    client = _client("http://deposit", "user", "pass")
    assert isinstance(client, PublicApiDepositClient)


def test_collection_error():
    mock_client = MagicMock()
    mock_client.service_document.return_value = {"error": "something went wrong"}

    with pytest.raises(InputError) as e:
        _collection(mock_client)

    assert "Service document retrieval: something went wrong" == str(e.value)


def test_collection_ok():
    mock_client = MagicMock()
    mock_client.service_document.return_value = EXAMPLE_SERVICE_DOCUMENT
    collection_name = _collection(mock_client)

    assert collection_name == "softcol"


def test_collection_ko_because_downtime():
    mock_client = MagicMock()
    mock_client.service_document.side_effect = MaintenanceError("downtime")
    with pytest.raises(MaintenanceError, match="downtime"):
        _collection(mock_client)


def test_deposit_with_server_down_for_maintenance(
    sample_archive, mocker, caplog, client_mock_api_down, slug, tmp_path
):
    """ Deposit failure due to maintenance down time should be explicit

    """
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "mock://deposit.swh/1",
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--name",
            "test-project",
            "--archive",
            sample_archive["path"],
            "--author",
            "Jane Doe",
        ],
    )

    assert result.exit_code == 1, result.output
    assert result.output == ""
    assert caplog.record_tuples == [
        (
            "swh.deposit.cli.client",
            logging.ERROR,
            "Database backend maintenance: Temporarily unavailable, try again later.",
        )
    ]

    client_mock_api_down.service_document.assert_called_once_with()


def test_single_minimal_deposit(
    sample_archive, mocker, caplog, client_mock, slug, tmp_path
):
    """ from:
    https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#single-deposit
    """  # noqa

    metadata_path = os.path.join(tmp_path, "metadata.xml")
    mocker.patch(
        "swh.deposit.cli.client.tempfile.TemporaryDirectory",
        return_value=contextlib.nullcontext(str(tmp_path)),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "mock://deposit.swh/1",
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--name",
            "test-project",
            "--archive",
            sample_archive["path"],
            "--author",
            "Jane Doe",
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.output == ""
    assert caplog.record_tuples == [
        ("swh.deposit.cli.client", logging.INFO, '{"foo": "bar"}'),
    ]

    client_mock.deposit_create.assert_called_once_with(
        archive=sample_archive["path"],
        collection="softcol",
        in_progress=False,
        metadata=metadata_path,
        slug=slug,
    )

    with open(metadata_path) as fd:
        assert (
            fd.read()
            == f"""\
<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" \
xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
\t<codemeta:name>test-project</codemeta:name>
\t<codemeta:identifier>{slug}</codemeta:identifier>
\t<codemeta:author>
\t\t<codemeta:name>Jane Doe</codemeta:name>
\t</codemeta:author>
</entry>"""
        )


def test_metadata_validation(sample_archive, mocker, caplog, tmp_path):
    """ from:
    https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#single-deposit
    """  # noqa
    slug = generate_slug()
    mocker.patch("swh.deposit.cli.client.generate_slug", return_value=slug)
    mock_client = MagicMock()
    mocker.patch("swh.deposit.cli.client._client", return_value=mock_client)
    mock_client.service_document.return_value = EXAMPLE_SERVICE_DOCUMENT
    mock_client.deposit_create.return_value = '{"foo": "bar"}'

    metadata_path = os.path.join(tmp_path, "metadata.xml")
    mocker.patch(
        "swh.deposit.cli.client.tempfile.TemporaryDirectory",
        return_value=contextlib.nullcontext(str(tmp_path)),
    )
    with open(metadata_path, "a"):
        pass  # creates the file

    runner = CliRunner()

    # Test missing author
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "mock://deposit.swh/1",
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--name",
            "test-project",
            "--archive",
            sample_archive["path"],
        ],
    )

    assert result.exit_code == 1, result.output
    assert result.output == ""
    assert len(caplog.record_tuples) == 1
    (_logger, level, message) = caplog.record_tuples[0]
    assert level == logging.ERROR
    assert " --author " in message

    # Clear mocking state
    caplog.clear()
    mock_client.reset_mock()

    # Test missing name
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "mock://deposit.swh/1",
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--archive",
            sample_archive["path"],
            "--author",
            "Jane Doe",
        ],
    )

    assert result.exit_code == 1, result.output
    assert result.output == ""
    assert len(caplog.record_tuples) == 1
    (_logger, level, message) = caplog.record_tuples[0]
    assert level == logging.ERROR
    assert " --name " in message

    # Clear mocking state
    caplog.clear()
    mock_client.reset_mock()

    # Test both --metadata and --author
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "mock://deposit.swh/1",
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--archive",
            sample_archive["path"],
            "--metadata",
            metadata_path,
            "--author",
            "Jane Doe",
        ],
    )

    assert result.exit_code == 1, result.output
    assert result.output == ""
    assert len(caplog.record_tuples) == 1
    (_logger, level, message) = caplog.record_tuples[0]
    assert level == logging.ERROR
    assert re.search("--metadata.*is incompatible with", message)

    # Clear mocking state
    caplog.clear()
    mock_client.reset_mock()


def test_single_deposit_slug_generation(
    sample_archive, mocker, caplog, tmp_path, client_mock
):
    """ from:
    https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#single-deposit
    """  # noqa
    slug = "my-slug"
    collection = "my-collection"

    metadata_path = os.path.join(tmp_path, "metadata.xml")
    mocker.patch(
        "swh.deposit.cli.client.tempfile.TemporaryDirectory",
        return_value=contextlib.nullcontext(str(tmp_path)),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "mock://deposit.swh/1",
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--name",
            "test-project",
            "--archive",
            sample_archive["path"],
            "--slug",
            slug,
            "--collection",
            collection,
            "--author",
            "Jane Doe",
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.output == ""
    assert caplog.record_tuples == [
        ("swh.deposit.cli.client", logging.INFO, '{"foo": "bar"}'),
    ]

    client_mock.deposit_create.assert_called_once_with(
        archive=sample_archive["path"],
        collection=collection,
        in_progress=False,
        metadata=metadata_path,
        slug=slug,
    )

    with open(metadata_path) as fd:
        assert (
            fd.read()
            == """\
<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" \
xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
\t<codemeta:name>test-project</codemeta:name>
\t<codemeta:identifier>my-slug</codemeta:identifier>
\t<codemeta:author>
\t\t<codemeta:name>Jane Doe</codemeta:name>
\t</codemeta:author>
</entry>"""
        )


def test_multisteps_deposit(
    sample_archive, atom_dataset, mocker, caplog, datadir, client_mock, slug
):
    """ from:
    https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#multisteps-deposit
    """  # noqa
    slug = generate_slug()
    mocker.patch("swh.deposit.cli.client.generate_slug", return_value=slug)

    # https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#create-an-incomplete-deposit
    client_mock.deposit_create.return_value = '{"deposit_id": "42"}'

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "mock://deposit.swh/1",
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--archive",
            sample_archive["path"],
            "--partial",
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.output == ""
    assert caplog.record_tuples == [
        ("swh.deposit.cli.client", logging.INFO, '{"deposit_id": "42"}'),
    ]

    client_mock.deposit_create.assert_called_once_with(
        archive=sample_archive["path"],
        collection="softcol",
        in_progress=True,
        metadata=None,
        slug=slug,
    )

    # Clear mocking state
    caplog.clear()
    client_mock.reset_mock()

    # https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#add-content-or-metadata-to-the-deposit

    metadata_path = os.path.join(datadir, "atom", "entry-data-deposit-binary.xml")

    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "mock://deposit.swh/1",
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--metadata",
            metadata_path,
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.output == ""
    assert caplog.record_tuples == [
        ("swh.deposit.cli.client", logging.INFO, '{"deposit_id": "42"}'),
    ]

    client_mock.deposit_create.assert_called_once_with(
        archive=None,
        collection="softcol",
        in_progress=False,
        metadata=metadata_path,
        slug=slug,
    )

    # Clear mocking state
    caplog.clear()
    client_mock.reset_mock()
