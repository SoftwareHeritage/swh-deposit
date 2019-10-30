# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.deposit.config import (
    PRIVATE_GET_RAW_CONTENT, PRIVATE_GET_DEPOSIT_METADATA, PRIVATE_PUT_DEPOSIT
)
from django.urls import reverse
from swh.model.hashutil import hash_to_bytes

from .common import get_stats, check_snapshot


def test_inject_deposit_ready(
        swh_config, requests_mock_datadir, datadir, deposit_loader):
    """Load a deposit which is ready

    """
    args = ['test', 999]
    archive_url = reverse(PRIVATE_GET_RAW_CONTENT, args=args)
    deposit_meta_url = reverse(PRIVATE_GET_DEPOSIT_METADATA, args=args)
    deposit_update_url = reverse(PRIVATE_PUT_DEPOSIT, args=args)

    # when
    res = deposit_loader.load(
        archive_url=archive_url,
        deposit_meta_url=deposit_meta_url,
        deposit_update_url=deposit_update_url)

    # then
    assert res['status'] == 'eventful'
    stats = get_stats(deposit_loader.storage)

    assert {
        'content': 303,
        'skipped_content': 0,
        'directory': 12,
        'origin': 1,
        'origin_visit': 1,
        'person': 1,
        'release': 0,
        'revision': 1,
        'snapshot': 1,
    } == stats

    origin_url = 'https://hal-test.archives-ouvertes.fr/some-external-id'
    rev_id = 'b1bef04d90ef3ba645df4c4f945748c173a4e9a2'
    dir_id = 'bed9acbf2a4502499f659e65a2ab77096bd46a1d'

    expected_revision = {
        'author': {
            'name': b'Software Heritage',
            'fullname': b'Software Heritage',
            'email': b'robot@softwareheritage.org'},
        'committer': {
            'name': b'Software Heritage',
            'fullname': b'Software Heritage',
            'email': b'robot@softwareheritage.org'},
        'committer_date': {
            'negative_utc': 'false',
            'offset': 0,
            'timestamp': {'microseconds': 0, 'seconds': 1507389428}},
        'date': {
            'negative_utc': 'false',
            'offset': 0,
            'timestamp': {'microseconds': 0, 'seconds': 1507389428}},
        'message': b'test: Deposit 999 in collection test',
        'metadata': {
            '@xmlns': ['http://www.w3.org/2005/Atom'],
            'author': ['some awesome author', 'another one', 'no one'],
            'codemeta:dateCreated': '2017-10-07T15:17:08Z',
            'external_identifier': 'some-external-id',
            'url': origin_url,
            'original_artifact': [
                {
                    'name': 'archive.zip',
                    'archive_type': 'tar',
                    'length': 725946,
                    'blake2s256': '04fffd328441d216c92492ad72d37388d8c77889880b069151298786fd48d889',  # noqa
                    'sha256': '31e066137a962676e89f69d1b65382de95a7ef7d914b8cb956f41ea72e0f516b',  # noqa
                    'sha1': 'f7bebf6f9c62a2295e889f66e05ce9bfaed9ace3',
                    'sha1_git': 'cae6b33cc33faafd2d6bd86c6b4273f9338c69c2'
                }
            ]
        },
        'synthetic': True,
        'type': 'tar',
        'parents': [],
        'directory': hash_to_bytes(dir_id),
        'id': hash_to_bytes(rev_id),
    }

    rev = next(deposit_loader.storage.revision_get([hash_to_bytes(rev_id)]))
    assert rev is not None
    assert expected_revision == rev

    expected_snapshot = {
        'id': '823109c16f9948c6f88cc5dec8e278da1487f06d',
        'branches': {
            'master': {
                'target': rev_id,
                'target_type': 'revision'
            }
        }
    }

    check_snapshot(expected_snapshot, deposit_loader.storage)
