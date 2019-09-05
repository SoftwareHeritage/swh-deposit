# Copyright (C) 2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest

from unittest.mock import MagicMock

from swh.deposit.client import PublicApiDepositClient
from swh.deposit.cli.client import _url, _client, _collection, InputError


def test_url():
    assert _url('http://deposit') == 'http://deposit/1'
    assert _url('https://other/1') == 'https://other/1'


def test_client():
    client = _client('http://deposit', 'user', 'pass')
    assert isinstance(client, PublicApiDepositClient)


def test_collection_error():
    mock_client = MagicMock()
    mock_client.service_document.return_value = {
        'error': 'something went wrong'
    }

    with pytest.raises(InputError) as e:
        _collection(mock_client)

    assert 'Service document retrieval: something went wrong' == str(e.value)


def test_collection_ok():
    mock_client = MagicMock()
    mock_client.service_document.return_value = {
        'service': {
            'workspace': {
                'collection': {
                    'sword:name': 'softcol',
                }
            }
        }
    }
    collection_name = _collection(mock_client)

    assert collection_name == 'softcol'
