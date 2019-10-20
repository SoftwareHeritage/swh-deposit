# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib
import os

from django.urls import reverse
import pytest
from rest_framework import status
from rest_framework.test import APITestCase

from swh.core import tarball
from swh.deposit.config import PRIVATE_GET_RAW_CONTENT
from swh.deposit.tests import TEST_CONFIG

from swh.deposit.tests.common import (
    BasicTestCase, WithAuthTestCase, CommonCreationRoutine,
    FileSystemCreationRoutine, create_arborescence_archive
)


@pytest.mark.fs
class DepositReadArchivesTest(APITestCase, WithAuthTestCase,
                              BasicTestCase, CommonCreationRoutine,
                              FileSystemCreationRoutine):

    def setUp(self):
        super().setUp()
        self.archive2 = create_arborescence_archive(
            self.root_path, 'archive2', 'file2', b'some other content in file')
        self.workdir = os.path.join(self.root_path, 'workdir')

    def private_deposit_url(self, deposit_id):
        return reverse(PRIVATE_GET_RAW_CONTENT,
                       args=[self.collection.name, deposit_id])

    def test_access_to_existing_deposit_with_one_archive(self):
        """Access to deposit should stream a 200 response with its raw content

        """
        deposit_id = self.create_simple_binary_deposit()

        url = self.private_deposit_url(deposit_id)
        r = self.client.get(url)

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r._headers['content-type'][1],
                         'application/octet-stream')

        # read the stream
        data = b''.join(r.streaming_content)
        actual_sha1 = hashlib.sha1(data).hexdigest()
        self.assertEqual(actual_sha1, self.archive['sha1sum'])

        # this does not touch the extraction dir so this should stay empty
        self.assertEqual(os.listdir(TEST_CONFIG['extraction_dir']), [])

    def _check_tarball_consistency(self, actual_sha1):
        tarball.uncompress(self.archive['path'], self.workdir)
        self.assertEqual(os.listdir(self.workdir), ['file1'])
        tarball.uncompress(self.archive2['path'], self.workdir)
        lst = set(os.listdir(self.workdir))
        self.assertEqual(lst, {'file1', 'file2'})

        new_path = self.workdir + '.zip'
        tarball.compress(new_path, 'zip', self.workdir)
        with open(new_path, 'rb') as f:
            h = hashlib.sha1(f.read()).hexdigest()

        self.assertEqual(actual_sha1, h)
        self.assertNotEqual(actual_sha1, self.archive['sha1sum'])
        self.assertNotEqual(actual_sha1, self.archive2['sha1sum'])

    def test_access_to_existing_deposit_with_multiple_archives(self):
        """Access to deposit should stream a 200 response with its raw contents

        """
        deposit_id = self.create_complex_binary_deposit()
        url = self.private_deposit_url(deposit_id)
        r = self.client.get(url)

        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r._headers['content-type'][1],
                         'application/octet-stream')
        # read the stream
        data = b''.join(r.streaming_content)
        actual_sha1 = hashlib.sha1(data).hexdigest()
        self._check_tarball_consistency(actual_sha1)

        # this touches the extraction directory but should clean up
        # after itself
        self.assertEqual(os.listdir(TEST_CONFIG['extraction_dir']), [])


@pytest.mark.fs
class DepositReadArchivesTest2(DepositReadArchivesTest):
    def private_deposit_url(self, deposit_id):
        return reverse(PRIVATE_GET_RAW_CONTENT+'-nc', args=[deposit_id])
