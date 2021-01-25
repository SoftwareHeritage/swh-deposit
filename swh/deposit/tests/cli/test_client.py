# Copyright (C) 2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import ast
from collections import OrderedDict
import contextlib
import json
import logging
import os
from unittest.mock import MagicMock

import pytest
import yaml

from swh.deposit.api.checks import check_metadata
from swh.deposit.cli import deposit as cli
from swh.deposit.cli.client import InputError, _collection, _url, generate_metadata
from swh.deposit.client import MaintenanceError, PublicApiDepositClient
from swh.deposit.parsers import parse_xml
from swh.model.exceptions import ValidationError

from ..conftest import TEST_USER


def generate_slug() -> str:
    """Generate a slug (sample purposes).

    """
    import uuid

    return str(uuid.uuid4())


@pytest.fixture
def datadir(request):
    """Override default datadir to target main test datadir"""
    return os.path.join(os.path.dirname(str(request.fspath)), "../data")


@pytest.fixture
def slug():
    return generate_slug()


@pytest.fixture
def patched_tmp_path(tmp_path, mocker):
    mocker.patch(
        "tempfile.TemporaryDirectory",
        return_value=contextlib.nullcontext(str(tmp_path)),
    )
    return tmp_path


@pytest.fixture
def client_mock_api_down(mocker, slug):
    """A mock client whose connection with api fails due to maintenance issue

    """
    mock_client = MagicMock()
    mocker.patch("swh.deposit.client.PublicApiDepositClient", return_value=mock_client)
    mock_client.service_document.side_effect = MaintenanceError(
        "Database backend maintenance: Temporarily unavailable, try again later."
    )
    return mock_client


def test_cli_url():
    assert _url("http://deposit") == "http://deposit/1"
    assert _url("https://other/1") == "https://other/1"


def test_cli_collection_error():
    mock_client = MagicMock()
    mock_client.service_document.return_value = {"error": "something went wrong"}

    with pytest.raises(InputError) as e:
        _collection(mock_client)

    assert "Service document retrieval: something went wrong" == str(e.value)


def test_cli_collection_ok(requests_mock_datadir):
    client = PublicApiDepositClient(
        url="https://deposit.swh.test/1", auth=("test", "test")
    )
    collection_name = _collection(client)
    assert collection_name == "test"


def test_cli_collection_ko_because_downtime():
    mock_client = MagicMock()
    mock_client.service_document.side_effect = MaintenanceError("downtime")
    with pytest.raises(MaintenanceError, match="downtime"):
        _collection(mock_client)


def test_cli_upload_conflictual_flags(
    datadir, requests_mock_datadir, cli_runner, atom_dataset, tmp_path,
):
    """Post metadata-only deposit through cli with invalid swhid raises

    """
    api_url_basename = "deposit.test.metadataonly"
    metadata = atom_dataset["entry-data-minimal"]
    metadata_path = os.path.join(tmp_path, "entry-data-minimal.xml")
    with open(metadata_path, "w") as f:
        f.write(metadata)

    with pytest.raises(InputError, match="both with different values"):
        # fmt: off
        cli_runner.invoke(
            cli,
            [
                "upload",
                "--url", f"https://{api_url_basename}/1",
                "--username", TEST_USER["username"],
                "--password", TEST_USER["password"],
                "--metadata", metadata_path,
                "--slug", "some-slug",  # deprecated flag
                "--create-origin", "some-other-slug",  # conflictual value, so raise
                "--format", "json",
            ],
            catch_exceptions=False,
        )
        # fmt: on


def test_cli_deposit_with_server_down_for_maintenance(
    sample_archive, caplog, client_mock_api_down, slug, patched_tmp_path, cli_runner
):
    """ Deposit failure due to maintenance down time should be explicit

    """
    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", "https://deposit.swh.test/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--name", "test-project",
            "--archive", sample_archive["path"],
            "--author", "Jane Doe",
        ],
    )
    # fmt: on

    assert result.exit_code == 1, result.output
    assert result.output == ""
    down_for_maintenance_log_record = (
        "swh.deposit.cli.client",
        logging.ERROR,
        "Database backend maintenance: Temporarily unavailable, try again later.",
    )
    assert down_for_maintenance_log_record in caplog.record_tuples

    client_mock_api_down.service_document.assert_called_once_with()


def test_cli_client_generate_metadata_ok(slug):
    """Generated metadata is well formed and pass service side metadata checks

    """
    actual_metadata_xml = generate_metadata(
        "deposit-client",
        "project-name",
        authors=["some", "authors"],
        external_id="external-id",
        create_origin="origin-url",
    )

    actual_metadata = dict(parse_xml(actual_metadata_xml))
    assert actual_metadata["atom:author"] == "deposit-client"
    assert actual_metadata["atom:title"] == "project-name"
    assert actual_metadata["atom:updated"] is not None
    assert actual_metadata["codemeta:name"] == "project-name"
    assert actual_metadata["codemeta:identifier"] == "external-id"
    assert actual_metadata["codemeta:author"] == [
        OrderedDict([("codemeta:name", "some")]),
        OrderedDict([("codemeta:name", "authors")]),
    ]
    assert (
        actual_metadata["swh:deposit"]["swh:create_origin"]["swh:origin"]["@url"]
        == "origin-url"
    )

    checks_ok, detail = check_metadata(actual_metadata)

    assert checks_ok is True
    assert detail is None


def test_cli_client_generate_metadata_ok2(slug):
    """Generated metadata is well formed and pass service side metadata checks

    """
    actual_metadata_xml = generate_metadata(
        "deposit-client", "project-name", authors=["some", "authors"],
    )

    actual_metadata = dict(parse_xml(actual_metadata_xml))
    assert actual_metadata["atom:author"] == "deposit-client"
    assert actual_metadata["atom:title"] == "project-name"
    assert actual_metadata["atom:updated"] is not None
    assert actual_metadata["codemeta:name"] == "project-name"
    assert actual_metadata["codemeta:author"] == [
        OrderedDict([("codemeta:name", "some")]),
        OrderedDict([("codemeta:name", "authors")]),
    ]
    assert actual_metadata.get("codemeta:identifier") is None
    assert actual_metadata.get("swh:deposit") is None

    checks_ok, detail = check_metadata(actual_metadata)

    assert checks_ok is True
    assert detail is None


def test_cli_single_minimal_deposit_with_slug(
    sample_archive, slug, patched_tmp_path, requests_mock_datadir, cli_runner, caplog,
):
    """ This ensure a single deposit upload through the cli is fine, cf.
    https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#single-deposit
    """  # noqa

    metadata_path = os.path.join(patched_tmp_path, "metadata.xml")
    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", "https://deposit.swh.test/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--name", "test-project",
            "--archive", sample_archive["path"],
            "--author", "Jane Doe",
            "--slug", slug,
            "--format", "json",
        ],
    )
    # fmt: on

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "deposit_id": "615",
        "deposit_status": "partial",
        "deposit_status_detail": None,
        "deposit_date": "Oct. 8, 2020, 4:57 p.m.",
    }

    with open(metadata_path) as fd:
        actual_metadata = dict(parse_xml(fd.read()))
        assert actual_metadata["atom:author"] == TEST_USER["username"]
        assert actual_metadata["codemeta:name"] == "test-project"
        assert actual_metadata["atom:title"] == "test-project"
        assert actual_metadata["atom:updated"] is not None
        assert actual_metadata["codemeta:identifier"] == slug
        assert actual_metadata["codemeta:author"] == OrderedDict(
            [("codemeta:name", "Jane Doe")]
        )

    count_warnings = 0
    for (_, log_level, _) in caplog.record_tuples:
        count_warnings += 1 if log_level == logging.WARNING else 0

    assert (
        count_warnings == 1
    ), "We should have 1 warning as we are using slug instead of create_origin"


def test_cli_single_minimal_deposit_with_create_origin(
    sample_archive, slug, patched_tmp_path, requests_mock_datadir, cli_runner, caplog,
):
    """ This ensure a single deposit upload through the cli is fine, cf.
    https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#single-deposit
    """  # noqa

    metadata_path = os.path.join(patched_tmp_path, "metadata.xml")
    origin = slug

    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", "https://deposit.swh.test/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--name", "test-project",
            "--archive", sample_archive["path"],
            "--author", "Jane Doe",
            "--create-origin", origin,
            "--format", "json",
        ],
    )
    # fmt: on

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "deposit_id": "615",
        "deposit_status": "partial",
        "deposit_status_detail": None,
        "deposit_date": "Oct. 8, 2020, 4:57 p.m.",
    }

    with open(metadata_path) as fd:
        actual_metadata = dict(parse_xml(fd.read()))
        assert actual_metadata["atom:author"] == TEST_USER["username"]
        assert actual_metadata["codemeta:name"] == "test-project"
        assert actual_metadata["atom:title"] == "test-project"
        assert actual_metadata["atom:updated"] is not None
        assert (
            actual_metadata["swh:deposit"]["swh:create_origin"]["swh:origin"]["@url"]
            == origin
        )
        assert actual_metadata["codemeta:author"] == OrderedDict(
            [("codemeta:name", "Jane Doe")]
        )

    count_warnings = 0
    for (_, log_level, _) in caplog.record_tuples:
        count_warnings += 1 if log_level == logging.WARNING else 0

    assert (
        count_warnings == 0
    ), "We should have no warning as we are using create_origin"


def test_cli_validation_metadata(
    sample_archive, caplog, patched_tmp_path, cli_runner, slug
):
    """Multiple metadata flags scenario (missing, conflicts) properly fails the calls

    """

    metadata_path = os.path.join(patched_tmp_path, "metadata.xml")
    with open(metadata_path, "a"):
        pass  # creates the file

    for flag_title_or_name, author_or_name in [
        ("--author", "no one"),
        ("--name", "test-project"),
    ]:
        # Test missing author then missing name
        # fmt: off
        result = cli_runner.invoke(
            cli,
            [
                "upload",
                "--url", "https://deposit.swh.test/1",
                "--username", TEST_USER["username"],
                "--password", TEST_USER["password"],
                "--archive", sample_archive["path"],
                "--slug", slug,
                flag_title_or_name,
                author_or_name,
            ],
        )
        # fmt: on

        assert result.exit_code == 1, f"unexpected result: {result.output}"
        assert result.output == ""
        expected_error_log_record = (
            "swh.deposit.cli.client",
            logging.ERROR,
            (
                "Problem during parsing options: "
                "For metadata deposit request, either a metadata file with "
                "--metadata or both --author and --name must be provided. "
            ),
        )
        assert expected_error_log_record in caplog.record_tuples

        # Clear mocking state
        caplog.clear()

        # incompatible flags: Test both --metadata and --author, then --metadata and
        # --name
        # fmt: off
        result = cli_runner.invoke(
            cli,
            [
                "upload",
                "--url", "https://deposit.swh.test/1",
                "--username", TEST_USER["username"],
                "--password", TEST_USER["password"],
                "--name", "test-project",
                "--deposit-id", 666,
                "--archive", sample_archive["path"],
                "--slug", slug,
            ],
        )
        # fmt: on
        assert result.exit_code == 1, f"unexpected result: {result.output}"
        assert result.output == ""
        expected_error_log_record = (
            "swh.deposit.cli.client",
            logging.ERROR,
            (
                "Problem during parsing options: "
                "For metadata deposit request, either a metadata file with "
                "--metadata or both --author and --name must be provided."
            ),
        )
        assert expected_error_log_record in caplog.record_tuples

        # Clear mocking state
        caplog.clear()

        # incompatible flags check (Test both --metadata and --author,
        # then --metadata and --name)
        # fmt: off
        result = cli_runner.invoke(
            cli,
            [
                "upload",
                "--url", "https://deposit.swh.test/1",
                "--username", TEST_USER["username"],
                "--password", TEST_USER["password"],
                "--archive", sample_archive["path"],
                "--metadata", metadata_path,
                "--author", "Jane Doe",
                "--slug", slug,
            ],
        )
        # fmt: on

        assert result.exit_code == 1, result.output
        assert result.output == ""
        expected_error_log_record = (
            "swh.deposit.cli.client",
            logging.ERROR,
            (
                "Problem during parsing options: "
                "Using --metadata flag is incompatible with --author "
                "and --name and --create-origin (those are used to generate "
                "one metadata file)."
            ),
        )
        assert expected_error_log_record in caplog.record_tuples
        caplog.clear()


def test_cli_validation_no_actionable_command(caplog, cli_runner):
    """Multiple metadata flags scenario (missing, conflicts) properly fails the calls

    """
    # no actionable command
    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", "https://deposit.swh.test/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--partial",
        ],
    )
    # fmt: on

    assert result.exit_code == 1, result.output
    assert result.output == ""
    expected_error_log_record = (
        "swh.deposit.cli.client",
        logging.ERROR,
        (
            "Problem during parsing options: "
            "Please provide an actionable command. See --help for more information"
        ),
    )
    assert expected_error_log_record in caplog.record_tuples


def test_cli_validation_replace_with_no_deposit_id_fails(
    sample_archive, caplog, patched_tmp_path, requests_mock_datadir, datadir, cli_runner
):
    """--replace flags require --deposit-id otherwise fails

    """
    metadata_path = os.path.join(datadir, "atom", "entry-data-deposit-binary.xml")

    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", "https://deposit.swh.test/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--metadata", metadata_path,
            "--archive", sample_archive["path"],
            "--replace",
        ],
    )
    # fmt: on

    assert result.exit_code == 1, result.output
    assert result.output == ""
    expected_error_log_record = (
        "swh.deposit.cli.client",
        logging.ERROR,
        (
            "Problem during parsing options: "
            "To update an existing deposit, you must provide its id"
        ),
    )
    assert expected_error_log_record in caplog.record_tuples


def test_cli_single_deposit_slug_generation(
    sample_archive, patched_tmp_path, requests_mock_datadir, cli_runner
):
    """Single deposit scenario without providing the slug, it should
    not be generated.
    """
    metadata_path = os.path.join(patched_tmp_path, "metadata.xml")
    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", "https://deposit.swh.test/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--name", "test-project",
            "--archive", sample_archive["path"],
            "--author", "Jane Doe",
            "--format", "json",
        ],
    )
    # fmt: on
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "deposit_id": "615",
        "deposit_status": "partial",
        "deposit_status_detail": None,
        "deposit_date": "Oct. 8, 2020, 4:57 p.m.",
    }

    with open(metadata_path) as fd:
        metadata_xml = fd.read()
        actual_metadata = dict(parse_xml(metadata_xml))
        assert "codemeta:identifier" not in actual_metadata


def test_cli_multisteps_deposit(
    sample_archive, datadir, slug, requests_mock_datadir, cli_runner
):
    """ First deposit a partial deposit (no metadata, only archive), then update the metadata part.
    https://docs.softwareheritage.org/devel/swh-deposit/getting-started.html#multisteps-deposit
    """  # noqa
    api_url = "https://deposit.test.metadata/1"
    deposit_id = 666

    # Create a partial deposit with only 1 archive
    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", api_url,
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--archive", sample_archive["path"],
            "--slug", slug,
            "--format", "json",
            "--partial",
        ],
    )
    # fmt: on

    assert result.exit_code == 0, f"unexpected output: {result.output}"
    actual_deposit = json.loads(result.output)
    assert actual_deposit == {
        "deposit_id": str(deposit_id),
        "deposit_status": "partial",
        "deposit_status_detail": None,
        "deposit_date": "Oct. 8, 2020, 4:57 p.m.",
    }

    # Update the partial deposit with only 1 archive
    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", api_url,
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--archive", sample_archive["path"],
            "--deposit-id", deposit_id,
            "--slug", slug,
            "--format", "json",
            "--partial",  # in-progress: True, because remains the metadata to upload
        ],
    )
    # fmt: on
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
    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", api_url,
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--metadata", metadata_path,
            "--deposit-id", deposit_id,
            "--slug", slug,
            "--format", "json",
        ],
        # this time, ^ we no longer flag it to partial, so the status changes to
        # in-progress false
    )
    # fmt: on
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
def test_cli_deposit_status_with_output_format(
    output_format, callable_fn, datadir, slug, requests_mock_datadir, caplog, cli_runner
):
    """Check deposit status cli with all possible output formats (json, yaml, logging).

    """
    api_url_basename = "deposit.test.status"
    deposit_id = 1033
    expected_deposit_status = {
        "deposit_id": str(deposit_id),
        "deposit_status": "done",
        "deposit_status_detail": (
            "The deposit has been successfully loaded into the "
            "Software Heritage archive"
        ),
        "deposit_swh_id": "swh:1:dir:ef04a768181417fbc5eef4243e2507915f24deea",
        "deposit_swh_id_context": "swh:1:dir:ef04a768181417fbc5eef4243e2507915f24deea;origin=https://www.softwareheritage.org/check-deposit-2020-10-08T13:52:34.509655;visit=swh:1:snp:c477c6ef51833127b13a86ece7d75e5b3cc4e93d;anchor=swh:1:rev:f26f3960c175f15f6e24200171d446b86f6f7230;path=/",  # noqa
        "deposit_external_id": "check-deposit-2020-10-08T13:52:34.509655",
    }

    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "status",
            "--url", f"https://{api_url_basename}/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--deposit-id", deposit_id,
            "--format", output_format,
        ],
    )
    # fmt: on
    assert result.exit_code == 0, f"unexpected output: {result.output}"

    if output_format == "logging":
        assert len(caplog.record_tuples) == 1
        # format: (<module>, <log-level>, <log-msg>)
        _, _, result_output = caplog.record_tuples[0]
    else:
        result_output = result.output

    actual_deposit = callable_fn(result_output)
    assert actual_deposit == expected_deposit_status


def test_cli_update_metadata_with_swhid_on_completed_deposit(
    datadir, requests_mock_datadir, cli_runner
):
    """Update new metadata on a completed deposit (status done) is ok
    """
    api_url_basename = "deposit.test.updateswhid"
    deposit_id = 123
    expected_deposit_status = {
        "deposit_external_id": "check-deposit-2020-10-08T13:52:34.509655",
        "deposit_id": str(deposit_id),
        "deposit_status": "done",
        "deposit_status_detail": (
            "The deposit has been successfully loaded into the "
            "Software Heritage archive"
        ),
        "deposit_swh_id": "swh:1:dir:ef04a768181417fbc5eef4243e2507915f24deea",
        "deposit_swh_id_context": "swh:1:dir:ef04a768181417fbc5eef4243e2507915f24deea;origin=https://www.softwareheritage.org/check-deposit-2020-10-08T13:52:34.509655;visit=swh:1:snp:c477c6ef51833127b13a86ece7d75e5b3cc4e93d;anchor=swh:1:rev:f26f3960c175f15f6e24200171d446b86f6f7230;path=/",  # noqa
    }

    assert expected_deposit_status["deposit_status"] == "done"
    assert expected_deposit_status["deposit_swh_id"] is not None

    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", f"https://{api_url_basename}/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--name", "test-project",
            "--author", "John Doe",
            "--deposit-id", deposit_id,
            "--swhid", expected_deposit_status["deposit_swh_id"],
            "--format", "json",
        ],
    )
    # fmt: on
    assert result.exit_code == 0, result.output
    actual_deposit_status = json.loads(result.output)
    assert "error" not in actual_deposit_status
    assert actual_deposit_status == expected_deposit_status


def test_cli_update_metadata_with_swhid_on_other_status_deposit(
    datadir, requests_mock_datadir, cli_runner
):
    """Update new metadata with swhid on other deposit status is not possible
    """
    api_url_basename = "deposit.test.updateswhid"
    deposit_id = 321

    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", f"https://{api_url_basename}/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--name", "test-project",
            "--author", "John Doe",
            "--deposit-id", deposit_id,
            "--swhid", "swh:1:dir:ef04a768181417fbc5eef4243e2507915f24deea",
            "--format", "json",
        ],
    )
    # fmt: on
    assert result.exit_code == 0, result.output
    actual_result = json.loads(result.output)
    assert "error" in actual_result
    assert actual_result == {
        "error": "You can only update metadata on deposit with status 'done'",
        "detail": "The deposit 321 has status 'partial'",
        "deposit_status": "partial",
        "deposit_id": 321,
    }


def test_cli_metadata_only_deposit_full_metadata_file(
    datadir, requests_mock_datadir, cli_runner, atom_dataset, tmp_path,
):
    """Post metadata-only deposit through cli

    The metadata file posted by the client already contains the swhid

    """
    api_url_basename = "deposit.test.metadataonly"
    swhid = "swh:1:dir:ef04a768181417fbc5eef4243e2507915f24deea"
    metadata = atom_dataset["entry-data-with-swhid"].format(swhid=swhid)
    metadata_path = os.path.join(tmp_path, "entry-data-with-swhid.xml")
    with open(metadata_path, "w") as m:
        m.write(metadata)

    expected_deposit_status = {
        "deposit_id": "100",
        "deposit_status": "done",
        "deposit_date": "2020-10-08T13:52:34.509655",
    }

    assert expected_deposit_status["deposit_status"] == "done"

    # fmt: off
    result = cli_runner.invoke(
        cli,
        [
            "metadata-only",
            "--url", f"https://{api_url_basename}/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--metadata", metadata_path,
            "--format", "json",
        ],
    )
    # fmt: on
    assert result.exit_code == 0, result.output
    actual_deposit_status = json.loads(result.output)
    assert "error" not in actual_deposit_status
    assert actual_deposit_status == expected_deposit_status


def test_cli_metadata_only_deposit_invalid_swhid(
    datadir, requests_mock_datadir, cli_runner, atom_dataset, tmp_path,
):
    """Post metadata-only deposit through cli with invalid swhid raises

    """
    api_url_basename = "deposit.test.metadataonly"
    invalid_swhid = "ssh:2:sth:xxx"
    metadata = atom_dataset["entry-data-with-swhid"].format(swhid=invalid_swhid)
    metadata_path = os.path.join(tmp_path, "entry-data-with-swhid.xml")
    with open(metadata_path, "w") as f:
        f.write(metadata)

    with pytest.raises(ValidationError, match="Invalid"):
        # fmt: off
        cli_runner.invoke(
            cli,
            [
                "metadata-only",
                "--url", f"https://{api_url_basename}/1",
                "--username", TEST_USER["username"],
                "--password", TEST_USER["password"],
                "--metadata", metadata_path,
                "--format", "json",
            ],
            catch_exceptions=False,
        )
        # fmt: on


def test_cli_metadata_only_deposit_no_swhid(
    datadir, requests_mock_datadir, cli_runner, atom_dataset, tmp_path,
):
    """Post metadata-only deposit through cli with invalid swhid raises

    """
    api_url_basename = "deposit.test.metadataonly"
    metadata = atom_dataset["entry-data-minimal"]
    metadata_path = os.path.join(tmp_path, "entry-data-minimal.xml")
    with open(metadata_path, "w") as f:
        f.write(metadata)

    with pytest.raises(InputError, match="SWHID must be provided"):
        # fmt: off
        cli_runner.invoke(
            cli,
            [
                "metadata-only",
                "--url", f"https://{api_url_basename}/1",
                "--username", TEST_USER["username"],
                "--password", TEST_USER["password"],
                "--metadata", metadata_path,
                "--format", "json",
            ],
            catch_exceptions=False,
        )
        # fmt: on


@pytest.mark.parametrize(
    "metadata_entry_key", ["entry-data-with-add-to-origin", "entry-only-create-origin"]
)
def test_cli_deposit_warning_missing_origin(
    sample_archive,
    metadata_entry_key,
    tmp_path,
    atom_dataset,
    caplog,
    cli_runner,
    requests_mock_datadir,
):
    """Deposit cli should log warning when the provided metadata xml is missing origins

    """
    # For the next deposit, no warning should be logged as either <swh:create_origin> or
    # <swh:origin_to_add> are provided

    metadata_raw = atom_dataset[metadata_entry_key] % "some-url"
    metadata_path = os.path.join(tmp_path, "metadata-with-origin-tag-to-deposit.xml")
    with open(metadata_path, "w") as f:
        f.write(metadata_raw)

    # fmt: off
    cli_runner.invoke(
        cli,
        [
            "upload",
            "--url", "https://deposit.swh.test/1",
            "--username", TEST_USER["username"],
            "--password", TEST_USER["password"],
            "--metadata", metadata_path,
        ],
    )
    # fmt: on

    for (_, log_level, _) in caplog.record_tuples:
        # all messages are info or below messages so everything is fine
        assert log_level < logging.WARNING
