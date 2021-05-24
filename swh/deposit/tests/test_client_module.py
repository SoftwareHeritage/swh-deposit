# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# Ensure the gist of the BaseDepositClient.execute works as expected in corner cases The
# following tests uses the ServiceDocumentDepositClient and StatusDepositClient because
# they are BaseDepositClient subclasses. We could have used other classes but those ones
# got elected as they are fairly simple ones.

import pytest

from swh.deposit.client import (
    MaintenanceError,
    ServiceDocumentDepositClient,
    StatusDepositClient,
)


def test_client_read_data_ok(requests_mock_datadir):
    client = ServiceDocumentDepositClient(
        url="https://deposit.swh.test/1", auth=("test", "test")
    )

    result = client.execute()

    assert isinstance(result, dict)

    collection = result["app:service"]["app:workspace"]["app:collection"]
    assert collection["sword:name"] == "test"


def test_client_read_data_fails(mocker):
    mock = mocker.patch("swh.deposit.client.BaseDepositClient.do_execute")
    mock.side_effect = ValueError("here comes trouble")

    client = ServiceDocumentDepositClient(
        url="https://deposit.swh.test/1", auth=("test", "test")
    )

    result = client.execute()
    assert isinstance(result, dict)
    assert "error" in result
    assert mock.called


def test_client_read_data_no_result(requests_mock):
    url = "https://deposit.swh.test/1"
    requests_mock.get(f"{url}/servicedocument/", status_code=204)

    client = ServiceDocumentDepositClient(
        url="https://deposit.swh.test/1", auth=("test", "test")
    )

    result = client.execute()
    assert isinstance(result, dict)
    assert result == {"status": 204}


def test_client_read_data_collection_error_503(requests_mock, atom_dataset):
    error_content = atom_dataset["error-cli"].format(
        summary="forbidden", verboseDescription="Access restricted",
    )
    url = "https://deposit.swh.test/1"
    requests_mock.get(f"{url}/servicedocument/", status_code=503, text=error_content)

    client = ServiceDocumentDepositClient(
        url="https://deposit.swh.test/1", auth=("test", "test")
    )

    result = client.execute()
    assert isinstance(result, dict)
    assert result == {
        "error": "forbidden",
        "status": 503,
        "collection": None,
    }


def test_client_read_data_status_error_503(requests_mock, atom_dataset):
    error_content = atom_dataset["error-cli"].format(
        summary="forbidden", verboseDescription="Access restricted",
    )
    collection = "test"
    deposit_id = 1
    url = "https://deposit.swh.test/1"
    requests_mock.get(
        f"{url}/{collection}/{deposit_id}/status/", status_code=503, text=error_content
    )

    client = StatusDepositClient(
        url="https://deposit.swh.test/1", auth=("test", "test")
    )

    with pytest.raises(MaintenanceError, match="forbidden"):
        client.execute(collection, deposit_id)
