# Copyright (C) 2019-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import ast
import contextlib
import json
import logging
import os
from unittest.mock import MagicMock

from click.testing import CliRunner
import pytest
import yaml

from swh.deposit.cli import deposit as cli
from swh.deposit.cli.client import InputError, _client, _collection, _url, generate_slug
from swh.deposit.client import MaintenanceError, PublicApiDepositClient
from swh.deposit.parsers import parse_xml

from ..conftest import TEST_USER


@pytest.fixture
def deposit_config():
    return {
        "url": "https://deposit.swh.test/1",
        "auth": {"username": "test", "password": "test",},
    }


@pytest.fixture
def datadir(request):
    """Override default datadir to target main test datadir"""
    return os.path.join(os.path.dirname(str(request.fspath)), "../data")


@pytest.fixture
def slug():
    return generate_slug()


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


def test_cli_url():
    assert _url("http://deposit") == "http://deposit/1"
    assert _url("https://other/1") == "https://other/1"


def test_cli_client():
    client = _client("http://deposit", "user", "pass")
    assert isinstance(client, PublicApiDepositClient)


def test_cli_collection_error():
    mock_client = MagicMock()
    mock_client.service_document.return_value = {"error": "something went wrong"}

    with pytest.raises(InputError) as e:
        _collection(mock_client)

    assert "Service document retrieval: something went wrong" == str(e.value)


def test_cli_collection_ok(deposit_config, requests_mock_datadir):
    client = PublicApiDepositClient(deposit_config)
    collection_name = _collection(client)
    assert collection_name == "test"


def test_cli_collection_ko_because_downtime():
    mock_client = MagicMock()
    mock_client.service_document.side_effect = MaintenanceError("downtime")
    with pytest.raises(MaintenanceError, match="downtime"):
        _collection(mock_client)


def test_cli_deposit_with_server_down_for_maintenance(
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
            "https://deposit.swh.test/1",
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
    down_for_maintenance_log_record = (
        "swh.deposit.cli.client",
        logging.ERROR,
        "Database backend maintenance: Temporarily unavailable, try again later.",
    )
    assert down_for_maintenance_log_record in caplog.record_tuples

    client_mock_api_down.service_document.assert_called_once_with()


def test_cli_single_minimal_deposit(
    sample_archive, mocker, slug, tmp_path, requests_mock_datadir
):
    """ This ensure a single deposit upload through the cli is fine, cf.
    https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#single-deposit
    """  # noqa

    metadata_path = os.path.join(tmp_path, "metadata.xml")
    mocker.patch(
        "tempfile.TemporaryDirectory",
        return_value=contextlib.nullcontext(str(tmp_path)),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "https://deposit.swh.test/1",
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
            "--slug",
            slug,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "deposit_id": "615",
        "deposit_status": "partial",
        "deposit_status_detail": None,
        "deposit_date": "Oct. 8, 2020, 4:57 p.m.",
    }

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


def test_cli_metadata_validation(
    sample_archive, mocker, caplog, tmp_path, requests_mock_datadir
):
    """Multiple metadata flags scenario (missing, conflicts) properly fails the calls

    """
    slug = generate_slug()

    metadata_path = os.path.join(tmp_path, "metadata.xml")
    mocker.patch(
        "tempfile.TemporaryDirectory",
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
            "https://deposit.swh.test/1",
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
        ],
    )

    assert result.exit_code == 1, f"unexpected result: {result.output}"
    assert result.output == ""
    expected_error_log_record = (
        "swh.deposit.cli.client",
        logging.ERROR,
        (
            "Problem during parsing options: Either a metadata file"
            " (--metadata) or both --author and --name must be provided, "
            "unless this is an archive-only deposit."
        ),
    )
    assert expected_error_log_record in caplog.record_tuples

    # Clear mocking state
    caplog.clear()

    # Test missing name
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "https://deposit.swh.test/1",
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--archive",
            sample_archive["path"],
            "--author",
            "Jane Doe",
            "--slug",
            slug,
        ],
    )

    assert result.exit_code == 1, result.output
    assert result.output == ""
    assert expected_error_log_record in caplog.record_tuples

    # Clear mocking state
    caplog.clear()

    # Test both --metadata and --author
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "https://deposit.swh.test/1",
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
            "--slug",
            slug,
        ],
    )

    assert result.exit_code == 1, result.output
    assert result.output == ""
    expected_error_log_record_2 = (
        "swh.deposit.cli.client",
        logging.ERROR,
        (
            "Problem during parsing options: Using a metadata file "
            "(--metadata) is incompatible with --author and --name, "
            "which are used to generate one."
        ),
    )
    assert expected_error_log_record_2 in caplog.record_tuples


def test_cli_single_deposit_slug_generation(
    sample_archive, mocker, tmp_path, requests_mock_datadir
):
    """Single deposit scenario without providing the slug, the slug is generated nonetheless
    https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#single-deposit
    """  # noqa
    metadata_path = os.path.join(tmp_path, "metadata.xml")
    mocker.patch(
        "tempfile.TemporaryDirectory",
        return_value=contextlib.nullcontext(str(tmp_path)),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            "https://deposit.swh.test/1",
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
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "deposit_id": "615",
        "deposit_status": "partial",
        "deposit_status_detail": None,
        "deposit_date": "Oct. 8, 2020, 4:57 p.m.",
    }

    with open(metadata_path) as fd:
        metadata_xml = fd.read()
        actual_metadata = parse_xml(metadata_xml)
        assert actual_metadata["codemeta:identifier"] is not None


def test_cli_multisteps_deposit(sample_archive, datadir, slug, requests_mock_datadir):
    """ First deposit a partial deposit (no metadata, only archive), then update the metadata part.
    https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#multisteps-deposit
    """  # noqa
    api_url = "https://deposit.test.metadata/1"
    deposit_id = 666

    runner = CliRunner()
    # Create a partial deposit with only 1 archive
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            api_url,
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--archive",
            sample_archive["path"],
            "--partial",
            "--slug",
            slug,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, f"unexpected output: {result.output}"
    actual_deposit = json.loads(result.output)
    assert actual_deposit == {
        "deposit_id": str(deposit_id),
        "deposit_status": "partial",
        "deposit_status_detail": None,
        "deposit_date": "Oct. 8, 2020, 4:57 p.m.",
    }

    # Update the partial deposit with only 1 archive
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            api_url,
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--archive",
            sample_archive["path"],
            "--deposit-id",
            deposit_id,
            "--partial",  # in-progress: True, because remains the metadata to upload
            "--slug",
            slug,
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, f"unexpected output: {result.output}"
    assert result.output is not None
    actual_deposit = json.loads(result.output)
    # deposit update scenario actually returns a deposit status dict
    assert actual_deposit["deposit_id"] == str(deposit_id)
    assert actual_deposit["deposit_status"] == "partial"

    # Update the partial deposit with only some metadata (and then finalize it)
    # https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#add-content-or-metadata-to-the-deposit
    metadata_path = os.path.join(datadir, "atom", "entry-data-deposit-binary.xml")

    # Update deposit with metadata
    result = runner.invoke(
        cli,
        [
            "upload",
            "--url",
            api_url,
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--metadata",
            metadata_path,
            "--deposit-id",
            deposit_id,
            "--slug",
            slug,
            "--format",
            "json",
        ],  # this time, ^ we no longer flag it to partial, so the status changes to
        # in-progress false
    )

    assert result.exit_code == 0, f"unexpected output: {result.output}"
    assert result.output is not None
    actual_deposit = json.loads(result.output)
    # deposit update scenario actually returns a deposit status dict
    assert actual_deposit["deposit_id"] == str(deposit_id)
    # FIXME: should be "deposited" but current limitation in the
    # requests_mock_datadir_visits use, cannot find a way to make it work right now
    assert actual_deposit["deposit_status"] == "partial"


@pytest.mark.parametrize(
    "output_format,callable_fn",
    [
        ("json", json.loads),
        ("yaml", yaml.safe_load),
        (
            "logging",
            ast.literal_eval,
        ),  # not enough though, the caplog fixture is needed
    ],
)
def test_cli_deposit_status_json(
    output_format, callable_fn, datadir, slug, requests_mock_datadir, caplog
):
    """Check deposit status cli with all possible output formats

    """
    api_url_basename = "deposit.test.status"
    deposit_id = 1033
    deposit_status_xml_path = os.path.join(
        datadir, f"https_{api_url_basename}", f"1_test_{deposit_id}_status"
    )
    with open(deposit_status_xml_path, "r") as f:
        deposit_status_xml = f.read()
    expected_deposit_dict = dict(parse_xml(deposit_status_xml))

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "status",
            "--url",
            f"https://{api_url_basename}/1",
            "--username",
            TEST_USER["username"],
            "--password",
            TEST_USER["password"],
            "--deposit-id",
            deposit_id,
            "--format",
            output_format,
        ],
    )
    assert result.exit_code == 0, f"unexpected output: {result.output}"

    if output_format == "logging":
        assert len(caplog.record_tuples) == 1
        # format: (<module>, <log-level>, <log-msg>)
        _, _, result_output = caplog.record_tuples[0]
    else:
        result_output = result.output

    actual_deposit = callable_fn(result_output)
    assert actual_deposit == expected_deposit_dict
