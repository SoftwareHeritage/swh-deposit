# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import hashlib
import os
import shutil
import tempfile

from django.core.urlresolvers import reverse
from nose.tools import istest
from nose.plugins.attrib import attr
from rest_framework import status
from rest_framework.test import APITestCase

from swh.loader.tar import tarball
from swh.deposit.config import PRIVATE_GET_RAW_CONTENT
from swh.deposit.tests import TEST_CONFIG

from ..common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine


def _create_arborescence_zip(root_path, archive_name, filename, content):
    root_path = '/tmp/swh-deposit/test/build-zip/'
    os.makedirs(root_path, exist_ok=True)
    archive_path_dir = tempfile.mkdtemp(dir=root_path)

    dir_path = os.path.join(archive_path_dir, archive_name)
    os.mkdir(dir_path)

    filepath = os.path.join(dir_path, filename)
    with open(filepath, 'wb') as f:
        f.write(content)

    zip_path = dir_path + '.zip'
    zip_path = tarball.compress(zip_path, 'zip', dir_path)

    with open(zip_path, 'rb') as f:
        sha1 = hashlib.sha1()
        for chunk in f:
            sha1.update(chunk)

    return archive_path_dir, zip_path, sha1.hexdigest()


@attr('fs')
class DepositReadArchivesTest(APITestCase, WithAuthTestCase, BasicTestCase,
                              CommonCreationRoutine):

    def setUp(self):
        super().setUp()

        root_path = '/tmp/swh-deposit/test/build-zip/'
        os.makedirs(root_path, exist_ok=True)

        archive_path_dir, zip_path, zip_sha1sum = _create_arborescence_zip(
            root_path, 'archive1', 'file1', b'some content in file')

        self.archive_path = zip_path
        self.archive_path_sha1sum = zip_sha1sum
        self.archive_path_dir = archive_path_dir

        archive_path_dir2, zip_path2, zip_sha1sum2 = _create_arborescence_zip(
            root_path, 'archive2', 'file2', b'some other content in file')

        self.archive_path2 = zip_path2
        self.archive_path_sha1sum2 = zip_sha1sum2
        self.archive_path_dir2 = archive_path_dir2

        self.workdir = tempfile.mkdtemp(dir=root_path)
        self.root_path = root_path

    def tearDown(self):
        shutil.rmtree(self.root_path)

    @istest
    def access_to_existing_deposit_with_one_archive(self):
        """Access to deposit should stream a 200 response with its raw content

        """
        deposit_id = self.create_simple_binary_deposit(
            archive_path=self.archive_path)

        url = reverse(PRIVATE_GET_RAW_CONTENT,
                      args=[self.collection.name, deposit_id])

        r = self.client.get(url)

        self.assertEquals(r.status_code, status.HTTP_200_OK)
        self.assertEquals(r._headers['content-type'][1],
                          'application/octet-stream')

        data = r.content
        actual_sha1 = hashlib.sha1(data).hexdigest()
        self.assertEquals(actual_sha1, self.archive_path_sha1sum)

        # this does not touch the extraction dir so this should stay empty
        self.assertEquals(os.listdir(TEST_CONFIG['extraction_dir']), [])

    def _check_tarball_consistency(self, actual_sha1):
        tarball.uncompress(self.archive_path, self.workdir)
        self.assertEquals(os.listdir(self.workdir), ['file1'])
        tarball.uncompress(self.archive_path2, self.workdir)
        self.assertEquals(os.listdir(self.workdir), ['file1', 'file2'])

        new_path = self.workdir + '.zip'
        tarball.compress(new_path, 'zip', self.workdir)
        with open(new_path, 'rb') as f:
            h = hashlib.sha1(f.read()).hexdigest()

        self.assertEqual(actual_sha1, h)
        self.assertNotEqual(actual_sha1, self.archive_path_sha1sum)
        self.assertNotEqual(actual_sha1, self.archive_path_sha1sum2)

    @istest
    def access_to_existing_deposit_with_multiple_archives(self):
        """Access to deposit should stream a 200 response with its raw contents

        """
        deposit_id = self.create_complex_binary_deposit(
            archive_path=self.archive_path,
            archive_path2=self.archive_path2)

        url = reverse(PRIVATE_GET_RAW_CONTENT,
                      args=[self.collection.name, deposit_id])

        r = self.client.get(url)

        self.assertEquals(r.status_code, status.HTTP_200_OK)
        self.assertEquals(r._headers['content-type'][1],
                          'application/octet-stream')
        data = r.content
        actual_sha1 = hashlib.sha1(data).hexdigest()
        self._check_tarball_consistency(actual_sha1)

        # this touches the extraction directory but should clean up
        # after itself
        self.assertEquals(os.listdir(TEST_CONFIG['extraction_dir']), [])


class DepositReadArchivesFailureTest(APITestCase, WithAuthTestCase,
                                     BasicTestCase, CommonCreationRoutine):
    @istest
    def access_to_nonexisting_deposit_returns_404_response(self):
        """Read unknown collection should return a 404 response

        """
        unknown_id = '999'
        url = reverse(PRIVATE_GET_RAW_CONTENT,
                      args=[self.collection.name, unknown_id])

        response = self.client.get(url)
        self.assertEqual(response.status_code,
                         status.HTTP_404_NOT_FOUND)
        self.assertIn('Deposit with id %s does not exist' % unknown_id,
                      response.content.decode('utf-8'))

    @istest
    def access_to_nonexisting_collection_returns_404_response(self):
        """Read unknown deposit should return a 404 response

        """
        collection_name = 'non-existing'
        deposit_id = self.create_deposit_partial()
        url = reverse(PRIVATE_GET_RAW_CONTENT,
                      args=[collection_name, deposit_id])

        response = self.client.get(url)
        self.assertEqual(response.status_code,
                         status.HTTP_404_NOT_FOUND)
        self.assertIn('Unknown collection name %s' % collection_name,
                      response.content.decode('utf-8'))
