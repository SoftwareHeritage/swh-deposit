# Copyright (C) 2016-2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import os
import unittest
import shutil

from nose.tools import istest
from nose.plugins.attrib import attr
from rest_framework.test import APITestCase

from swh.model import hashutil
from swh.deposit.injection.loader import DepositLoader, DepositClient
from swh.deposit.config import PRIVATE_GET_RAW_CONTENT
from swh.deposit.config import PRIVATE_GET_DEPOSIT_METADATA
from swh.deposit.config import PRIVATE_PUT_DEPOSIT
from django.core.urlresolvers import reverse


from . import TEST_LOADER_CONFIG
from .common import BasicTestCase, WithAuthTestCase, CommonCreationRoutine
from .common import FileSystemCreationRoutine


class DepositLoaderInhibitsStorage:
    """Mixin class to inhibit the persistence and keep in memory the data
    sent for storage.

    cf. SWHDepositLoaderNoStorage

    """
    def __init__(self):
        super().__init__()
        # typed data
        self.state = {
            'origin': [],
            'origin_visit': [],
            'content': [],
            'directory': [],
            'revision': [],
            'release': [],
            'occurrence': [],
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

    def maybe_load_contents(self, contents):
        self._add('content', contents)

    def maybe_load_directories(self, directories):
        self._add('directory', directories)

    def maybe_load_revisions(self, revisions):
        self._add('revision', revisions)

    def maybe_load_releases(self, releases):
        self._add('release', releases)

    def maybe_load_occurrences(self, occurrences):
        self._add('occurrence', occurrences)

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
    def assertRevisionsOk(self, expected_revisions):
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


class SWHDepositLoaderNoStorage(DepositLoaderInhibitsStorage, DepositLoader):
    """Loader to test.

       It inherits from the actual deposit loader to actually test its
       correct behavior.  It also inherits from
       DepositLoaderInhibitsStorageLoader so that no persistence takes place.

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

        self.server = 'http://localhost/'

        # 1. create a deposit with archive and metadata
        self.deposit_id = self.create_simple_binary_deposit()

        me = self

        class SWHDepositTestClient(DepositClient):
            def get_archive(self, archive_update_url, archive_path,
                            log=None):
                r = me.client.get(archive_update_url)
                # import os
                # os.makedirs(os.path.dirname(archive_path), exist_ok=True)
                with open(archive_path, 'wb') as f:
                    for chunk in r.streaming_content:
                        f.write(chunk)

                return archive_path

            def get_metadata(self, metadata_url, log=None):
                r = me.client.get(metadata_url)
                return json.loads(r.content.decode('utf-8'))

            def update_deposit_status(self, update_status_url, status,
                                      revision_id=None):
                payload = {'status': status}
                if revision_id:
                    payload['revision_id'] = revision_id
                    me.client.put(update_status_url,
                                  content_type='application/json',
                                  data=json.dumps(payload))

        # 2. setup loader with no persistence
        self.loader = SWHDepositLoaderNoStorage()
        # and a basic client which accesses the data
        # setuped in that test
        self.loader.client = SWHDepositTestClient()

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
        self.assertEquals(len(self.loader.state['occurrence']), 1)

        # FIXME enrich state introspection
        # expected_revisions = {}
        # self.assertRevisionsOk(expected_revisions)