# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import unittest
import shutil

import pytest
from rest_framework.test import APITestCase

from swh.model import hashutil
from swh.deposit.models import Deposit
from swh.deposit.loader import loader
from swh.deposit.config import (
    PRIVATE_GET_RAW_CONTENT, PRIVATE_GET_DEPOSIT_METADATA, PRIVATE_PUT_DEPOSIT
)
from django.urls import reverse
from swh.loader.core.tests import BaseLoaderStorageTest

from swh.deposit import utils

from .common import SWHDepositTestClient, CLIENT_TEST_CONFIG
from .. import TEST_LOADER_CONFIG
from ..common import (BasicTestCase, WithAuthTestCase,
                      CommonCreationRoutine,
                      FileSystemCreationRoutine)


class TestLoaderUtils(unittest.TestCase):
    def assertRevisionsOk(self, expected_revisions):  # noqa: N802
        """Check the loader's revisions match the expected revisions.

        Expects self.loader to be instantiated and ready to be
        inspected (meaning the loading took place).

        Args:
            expected_revisions (dict): Dict with key revision id,
            value the targeted directory id.

        """
        # The last revision being the one used later to start back from
        for rev in self.loader.state['revision']:
            rev_id = hashutil.hash_to_hex(rev['id'])
            directory_id = hashutil.hash_to_hex(rev['directory'])

            self.assertEqual(expected_revisions[rev_id], directory_id)


@pytest.mark.fs
class DepositLoaderScenarioTest(APITestCase, WithAuthTestCase,
                                BasicTestCase, CommonCreationRoutine,
                                FileSystemCreationRoutine, TestLoaderUtils,
                                BaseLoaderStorageTest):

    def setUp(self):
        super().setUp()

        # create the extraction dir used by the loader
        os.makedirs(TEST_LOADER_CONFIG['extraction_dir'], exist_ok=True)

        # Sets a basic client which accesses the test data
        loader_client = SWHDepositTestClient(self.client,
                                             config=CLIENT_TEST_CONFIG)
        # Setup loader with that client
        self.loader = loader.DepositLoader(client=loader_client)

        self.storage = self.loader.storage

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(TEST_LOADER_CONFIG['extraction_dir'])

    def test_inject_deposit_ready(self):
        """Load a deposit which is ready

        """
        # create a deposit with archive and metadata
        deposit_id = self.create_simple_binary_deposit()
        self.update_binary_deposit(deposit_id, status_partial=False)

        args = [self.collection.name, deposit_id]

        archive_url = reverse(PRIVATE_GET_RAW_CONTENT, args=args)
        deposit_meta_url = reverse(PRIVATE_GET_DEPOSIT_METADATA, args=args)
        deposit_update_url = reverse(PRIVATE_PUT_DEPOSIT, args=args)

        # when
        res = self.loader.load(archive_url=archive_url,
                               deposit_meta_url=deposit_meta_url,
                               deposit_update_url=deposit_update_url)

        # then
        self.assertEqual(res['status'], 'eventful', res)
        self.assertCountContents(1)
        self.assertCountDirectories(1)
        self.assertCountRevisions(1)
        self.assertCountReleases(0)
        self.assertCountSnapshots(1)

    def test_inject_deposit_verify_metadata(self):
        """Load a deposit with metadata, test metadata integrity

        """
        deposit_id = self.create_simple_binary_deposit()
        self.add_metadata_to_deposit(deposit_id, status_partial=False)
        args = [self.collection.name, deposit_id]

        archive_url = reverse(PRIVATE_GET_RAW_CONTENT, args=args)
        deposit_meta_url = reverse(PRIVATE_GET_DEPOSIT_METADATA, args=args)
        deposit_update_url = reverse(PRIVATE_PUT_DEPOSIT, args=args)

        # when
        self.loader.load(archive_url=archive_url,
                         deposit_meta_url=deposit_meta_url,
                         deposit_update_url=deposit_update_url)

        # then
        self.assertCountContents(1)
        self.assertCountDirectories(1)
        self.assertCountRevisions(1)
        self.assertCountReleases(0)
        self.assertCountSnapshots(1)

        codemeta = 'codemeta:'
        deposit = Deposit.objects.get(pk=deposit_id)
        origin_url = utils.origin_url_from(deposit)

        expected_origin_metadata = {
            '@xmlns': 'http://www.w3.org/2005/Atom',
            '@xmlns:codemeta': 'https://doi.org/10.5063/SCHEMA/CODEMETA-2.0',
            'author': {
                'email': 'hal@ccsd.cnrs.fr',
                'name': 'HAL'
            },
            codemeta + 'url': 'https://hal-test.archives-ouvertes.fr/hal-01243065',  # same as xml  # noqa
            codemeta + 'runtimePlatform': 'phpstorm',
            codemeta + 'license': [
                {
                    codemeta + 'name': 'GNU General Public License v3.0 only'
                },
                {
                    codemeta + 'name': 'CeCILL Free Software License Agreement v1.1'  # noqa
                }
            ],
            codemeta + 'author': {
                codemeta + 'name': 'Morane Gruenpeter'
            },
            codemeta + 'programmingLanguage': ['php', 'python', 'C'],
            codemeta + 'applicationCategory': 'test',
            codemeta + 'dateCreated': '2017-05-03T16:08:47+02:00',
            codemeta + 'version': '1',
            'external_identifier': 'hal-01243065',
            'title': 'Composing a Web of Audio Applications',
            codemeta + 'description': 'this is the description',
            'id': 'hal-01243065',
            'client': 'hal',
            codemeta + 'keywords': 'DSP programming,Web',
            codemeta + 'developmentStatus': 'stable'
        }
        self.assertOriginMetadataContains('deposit', origin_url,
                                          expected_origin_metadata)

        self.assertRegex(deposit.swh_id, r'^swh:1:dir:.*')
        self.assertEqual(deposit.swh_id_context, '%s;origin=%s' % (
            deposit.swh_id, origin_url
        ))
        self.assertRegex(deposit.swh_anchor_id, r'^swh:1:rev:.*')
        self.assertEqual(deposit.swh_anchor_id_context, '%s;origin=%s' % (
            deposit.swh_anchor_id, origin_url
        ))
