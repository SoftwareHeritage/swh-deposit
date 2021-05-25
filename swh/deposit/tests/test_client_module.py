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
    CollectionListDepositClient,
    MaintenanceError,
    PublicApiDepositClient,
    ServiceDocumentDepositClient,
    StatusDepositClient,
)
from swh.deposit.utils import to_header_link


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


EXPECTED_DEPOSIT = {
    "id": "1031",
    "external_id": "check-deposit-2020-10-09T13:10:00.000000",
    "status": "rejected",
    "status_detail": "Deposit without archive",
}

EXPECTED_DEPOSIT2 = {
    "id": "1032",
    "external_id": "check-deposit-2020-10-10T13:20:00.000000",
    "status": "rejected",
    "status_detail": "Deposit without archive",
}

EXPECTED_DEPOSIT3 = {
    "id": "1033",
    "external_id": "check-deposit-2020-10-08T13:52:34.509655",
    "status": "done",
    "status_detail": (
        "The deposit has been successfully loaded into the Software " "Heritage archive"
    ),
    "reception_date": "2020-10-08T13:50:30",
    "complete_date": "2020-10-08T13:52:34.509655",
    "swhid": "swh:1:dir:ef04a768181417fbc5eef4243e2507915f24deea",
    "swhid_context": "swh:1:dir:ef04a768181417fbc5eef4243e2507915f24deea;origin=https://www.softwareheritage.org/check-deposit-2020-10-08T13:52:34.509655;visit=swh:1:snp:c477c6ef51833127b13a86ece7d75e5b3cc4e93d;anchor=swh:1:rev:f26f3960c175f15f6e24200171d446b86f6f7230;path=/",  # noqa
}


def test_client_collection_list(requests_mock, atom_dataset):
    collection_list_xml = atom_dataset["entry-list-deposits"]
    base_url = "https://deposit.test.list/1"
    collection = "test"
    url = f"{base_url}/{collection}/"
    requests_mock.get(url, status_code=200, text=collection_list_xml)
    expected_result = {
        "count": "3",
        "deposits": [EXPECTED_DEPOSIT, EXPECTED_DEPOSIT2, EXPECTED_DEPOSIT3],
    }

    # use dedicated client
    client = CollectionListDepositClient(url=base_url, auth=("test", "test"))

    # no pagination
    result = client.execute(collection)

    assert result == expected_result

    # The main public client should work the same way
    client2 = PublicApiDepositClient(url=base_url, auth=("test", "test"))
    result2 = client2.deposit_list(collection)

    assert result2 == expected_result

    assert requests_mock.called
    request_history = [m.url for m in requests_mock.request_history]
    assert request_history == [url] * 2


def test_client_collection_list_with_pagination_headers(requests_mock, atom_dataset):
    collection_list_xml_page1 = atom_dataset["entry-list-deposits-page1"]
    collection_list_xml_page2 = atom_dataset["entry-list-deposits-page2"]
    base_url = "https://deposit.test.list/1"
    collection = "test"
    url = f"{base_url}/{collection}/"
    page1 = 1
    page2 = 2
    page_size = 10
    url_page1 = f"{url}?page={page1}"
    url_page2 = f"{url}?page={page2}&page_size={page_size}"
    requests_mock.get(
        url_page1,
        status_code=200,
        text=collection_list_xml_page1,
        headers={"Link": to_header_link(url_page2, "next"),},
    )
    requests_mock.get(
        url_page2,
        status_code=200,
        text=collection_list_xml_page2,
        headers={"Link": to_header_link(url_page1, "previous"),},
    )

    expected_result_page1 = {
        "count": "3",
        "deposits": [EXPECTED_DEPOSIT, EXPECTED_DEPOSIT2],
        "next": url_page2,
    }
    expected_result_page2 = {
        "count": "3",
        "deposits": [EXPECTED_DEPOSIT3],
        "previous": url_page1,
    }

    client = CollectionListDepositClient(
        url="https://deposit.test.list/1", auth=("test", "test")
    )
    client2 = PublicApiDepositClient(url=base_url, auth=("test", "test"))

    result = client.execute(collection, page=page1)
    assert result == expected_result_page1

    result2 = client.execute(collection, page=page2, page_size=page_size)
    assert result2 == expected_result_page2

    # The main public client should work the same way
    result = client2.deposit_list(collection, page=page1)
    assert result == expected_result_page1

    result2 = client2.deposit_list(collection, page=page2, page_size=page_size)
    assert result2 == expected_result_page2

    assert requests_mock.called
    request_history = [m.url for m in requests_mock.request_history]
    assert request_history == [url_page1, url_page2] * 2
