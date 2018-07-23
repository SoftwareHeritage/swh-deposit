# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import unittest
import shutil

from nose.tools import istest
from nose.plugins.attrib import attr
from rest_framework.test import APITestCase

from swh.model import hashutil
from swh.deposit.models import Deposit
from swh.deposit.loader import loader
from swh.deposit.config import (
    PRIVATE_GET_RAW_CONTENT, PRIVATE_GET_DEPOSIT_METADATA, PRIVATE_PUT_DEPOSIT
)
from django.core.urlresolvers import reverse


from .common import SWHDepositTestClient, CLIENT_TEST_CONFIG
from .. import TEST_LOADER_CONFIG
from ..common import (BasicTestCase, WithAuthTestCase,
                      CommonCreationRoutine,
                      FileSystemCreationRoutine)


TOOL_ID = 99
PROVIDER_ID = 12


class DepositLoaderInhibitsStorage:
    """Mixin class to inhibit the persistence and keep in memory the data
    sent for storage.

    cf. SWHDepositLoaderNoStorage

    """
    def __init__(self, client=None):
        # client is not used here, transit it nonetheless to other mixins
        super().__init__(client=client)
        # typed data
        self.state = {
            'origin': [],
            'origin_visit': [],
            'origin_metadata': [],
            'content': [],
            'directory': [],
            'revision': [],
            'release': [],
            'snapshot': [],
            'tool': [],
            'provider': []
        }

    def _add(self, type, l):
        """Add without duplicates and keeping the insertion order.

        Args:
            type (str): Type of objects concerned by the action
            l ([object]): List of 'type' object

        """
        col = self.state[type]
        for o in l:
            if o in col:
                continue
            col.extend([o])

    def send_origin(self, origin):
        origin.update({'id': 1})
        self._add('origin', [origin])
        return origin['id']

    def send_origin_visit(self, origin_id, visit_date):
        origin_visit = {
            'origin': origin_id,
            'visit_date': visit_date,
            'visit': 1,
        }
        self._add('origin_visit', [origin_visit])
        return origin_visit

    def send_origin_metadata(self, origin_id, visit_date, provider_id, tool_id,
                             metadata):
        origin_metadata = {
            'origin_id': origin_id,
            'visit_date': visit_date,
            'provider_id': provider_id,
            'tool_id': tool_id,
            'metadata': metadata
        }
        self._add('origin_metadata', [origin_metadata])
        return origin_metadata

    def send_tool(self, tool):
        tool = {
            'tool_name': tool['tool_name'],
            'tool_version': tool['tool_version'],
            'tool_configuration': tool['tool_configuration']
        }
        self._add('tool', [tool])
        tool_id = TOOL_ID
        return tool_id

    def send_provider(self, provider):
        provider = {
            'provider_name': provider['provider_name'],
            'provider_type': provider['provider_type'],
            'provider_url': provider['provider_url'],
            'metadata': provider['metadata']
        }
        self._add('provider', [provider])
        provider_id = PROVIDER_ID
        return provider_id

    def maybe_load_contents(self, contents):
        self._add('content', contents)

    def maybe_load_directories(self, directories):
        self._add('directory', directories)

    def maybe_load_revisions(self, revisions):
        self._add('revision', revisions)

    def maybe_load_releases(self, releases):
        self._add('release', releases)

    def maybe_load_snapshot(self, snapshot):
        self._add('snapshot', [snapshot])

    def open_fetch_history(self):
        pass

    def close_fetch_history_failure(self, fetch_history_id):
        pass

    def close_fetch_history_success(self, fetch_history_id):
        pass

    def update_origin_visit(self, origin_id, visit, status):
        self.status = status

    # Override to do nothing at the end
    def close_failure(self):
        pass

    def close_success(self):
        pass


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

            self.assertEquals(expected_revisions[rev_id], directory_id)


class SWHDepositLoaderNoStorage(DepositLoaderInhibitsStorage,
                                loader.DepositLoader):
    """Loader to test.

       It inherits from the actual deposit loader to actually test its
       correct behavior.  It also inherits from
       DepositLoaderInhibitsStorage so that no persistence takes place.

    """
    pass


@attr('fs')
class DepositLoaderScenarioTest(APITestCase, WithAuthTestCase,
                                BasicTestCase, CommonCreationRoutine,
                                FileSystemCreationRoutine, TestLoaderUtils):

    def setUp(self):
        super().setUp()

        # create the extraction dir used by the loader
        os.makedirs(TEST_LOADER_CONFIG['extraction_dir'], exist_ok=True)

        # 1. create a deposit with archive and metadata
        self.deposit_id = self.create_simple_binary_deposit()
        # 2. Sets a basic client which accesses the test data
        loader_client = SWHDepositTestClient(self.client,
                                             config=CLIENT_TEST_CONFIG)
        # 3. setup loader with no persistence and that client
        self.loader = SWHDepositLoaderNoStorage(client=loader_client)

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(TEST_LOADER_CONFIG['extraction_dir'])

    @istest
    def inject_deposit_ready(self):
        """Load a deposit which is ready

        """
        args = [self.collection.name, self.deposit_id]

        archive_url = reverse(PRIVATE_GET_RAW_CONTENT, args=args)
        deposit_meta_url = reverse(PRIVATE_GET_DEPOSIT_METADATA, args=args)
        deposit_update_url = reverse(PRIVATE_PUT_DEPOSIT, args=args)

        # when
        self.loader.load(archive_url=archive_url,
                         deposit_meta_url=deposit_meta_url,
                         deposit_update_url=deposit_update_url)

        # then
        self.assertEquals(len(self.loader.state['content']), 1)
        self.assertEquals(len(self.loader.state['directory']), 1)
        self.assertEquals(len(self.loader.state['revision']), 1)
        self.assertEquals(len(self.loader.state['release']), 0)
        self.assertEquals(len(self.loader.state['snapshot']), 1)

    @istest
    def inject_deposit_verify_metadata(self):
        """Load a deposit with metadata, test metadata integrity

        """
        self.deposit_metadata_id = self.add_metadata_to_deposit(
            self.deposit_id)
        args = [self.collection.name, self.deposit_metadata_id]

        archive_url = reverse(PRIVATE_GET_RAW_CONTENT, args=args)
        deposit_meta_url = reverse(PRIVATE_GET_DEPOSIT_METADATA, args=args)
        deposit_update_url = reverse(PRIVATE_PUT_DEPOSIT, args=args)

        # when
        self.loader.load(archive_url=archive_url,
                         deposit_meta_url=deposit_meta_url,
                         deposit_update_url=deposit_update_url)

        # then
        self.assertEquals(len(self.loader.state['content']), 1)
        self.assertEquals(len(self.loader.state['directory']), 1)
        self.assertEquals(len(self.loader.state['revision']), 1)
        self.assertEquals(len(self.loader.state['release']), 0)
        self.assertEquals(len(self.loader.state['snapshot']), 1)
        self.assertEquals(len(self.loader.state['origin_metadata']), 1)
        self.assertEquals(len(self.loader.state['tool']), 1)
        self.assertEquals(len(self.loader.state['provider']), 1)

        codemeta = 'codemeta:'
        origin_url = 'https://hal-test.archives-ouvertes.fr/hal-01243065'
        expected_origin_metadata = {
            '@xmlns': 'http://www.w3.org/2005/Atom',
            '@xmlns:codemeta': 'https://doi.org/10.5063/SCHEMA/CODEMETA-2.0',
            'author': {
                'email': 'hal@ccsd.cnrs.fr',
                'name': 'HAL'
            },
            codemeta + 'url': origin_url,
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
        result = self.loader.state['origin_metadata'][0]
        self.assertEquals(result['metadata'], expected_origin_metadata)
        self.assertEquals(result['tool_id'], TOOL_ID)
        self.assertEquals(result['provider_id'], PROVIDER_ID)

        deposit = Deposit.objects.get(pk=self.deposit_id)

        self.assertRegex(deposit.swh_id, r'^swh:1:dir:.*')
        self.assertEquals(deposit.swh_id_context, '%s;origin=%s' % (
            deposit.swh_id, origin_url
        ))
        self.assertRegex(deposit.swh_anchor_id, r'^swh:1:rev:.*')
        self.assertEquals(deposit.swh_anchor_id_context, '%s;origin=%s' % (
            deposit.swh_anchor_id, origin_url
        ))
