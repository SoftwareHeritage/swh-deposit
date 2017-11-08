# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import base64
import hashlib
import os
import shutil
import tempfile

from django.core.urlresolvers import reverse
from django.test import TestCase
from io import BytesIO
from nose.plugins.attrib import attr
from rest_framework import status

from swh.deposit.config import COL_IRI, EM_IRI, EDIT_SE_IRI
from swh.deposit.models import DepositClient, DepositCollection
from swh.deposit.models import DepositRequestType
from swh.deposit.parsers import parse_xml
from swh.deposit.settings.testing import MEDIA_ROOT
from swh.loader.tar import tarball


def create_arborescence_zip(root_path, archive_name, filename, content,
                            up_to_size=None):
    """Build an archive named archive_name in the root_path.
    This archive contains one file named filename with the content content.

    Returns:
        dict with the keys:
        - dir: the directory of that archive
        - path: full path to the archive
        - sha1sum: archive's sha1sum
        - length: archive's length

    """
    os.makedirs(root_path, exist_ok=True)
    archive_path_dir = tempfile.mkdtemp(dir=root_path)

    dir_path = os.path.join(archive_path_dir, archive_name)
    os.mkdir(dir_path)

    filepath = os.path.join(dir_path, filename)
    l = len(content)
    count = 0
    batch_size = 128
    with open(filepath, 'wb') as f:
        f.write(content)
        if up_to_size:  # fill with blank content up to a given size
            count += l
            while count < up_to_size:
                f.write(b'0'*batch_size)
                count += batch_size

    zip_path = dir_path + '.zip'
    zip_path = tarball.compress(zip_path, 'zip', dir_path)

    with open(zip_path, 'rb') as f:
        length = 0
        sha1sum = hashlib.sha1()
        md5sum = hashlib.md5()
        data = b''
        for chunk in f:
            sha1sum.update(chunk)
            md5sum.update(chunk)
            length += len(chunk)
            data += chunk

    return {
        'dir': archive_path_dir,
        'name': archive_name,
        'data': data,
        'path': zip_path,
        'sha1sum': sha1sum.hexdigest(),
        'md5sum': md5sum.hexdigest(),
        'length': length,
    }


@attr('fs')
class FileSystemCreationRoutine(TestCase):
    """Mixin intended for tests needed to tamper with archives.

    """
    def setUp(self):
        """Define the test client and other test variables."""
        super().setUp()
        self.root_path = '/tmp/swh-deposit/test/build-zip/'
        os.makedirs(self.root_path, exist_ok=True)

        self.archive = create_arborescence_zip(
            self.root_path, 'archive1', 'file1', b'some content in file')

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.root_path)

    def create_simple_binary_deposit(self, status_partial=False):
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/zip',
            data=self.archive['data'],
            CONTENT_LENGTH=self.archive['length'],
            HTTP_MD5SUM=self.archive['md5sum'],
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS=status_partial,
            HTTP_CONTENT_DISPOSITION='attachment; filename=%s' % (
                self.archive['name'], ))

        # then
        assert response.status_code == status.HTTP_201_CREATED
        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']
        return deposit_id

    def create_complex_binary_deposit(self, status_partial=False):
        deposit_id = self.create_simple_binary_deposit(
            status_partial=True)

        # Add a second archive to the deposit
        # update its status to DEPOSIT_STATUS_READY
        response = self.client.post(
            reverse(EM_IRI, args=[self.collection.name, deposit_id]),
            content_type='application/zip',
            data=self.archive2['data'],
            CONTENT_LENGTH=self.archive2['length'],
            HTTP_MD5SUM=self.archive2['md5sum'],
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS=status_partial,
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename1.zip')

        # then
        assert response.status_code == status.HTTP_201_CREATED
        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']
        return deposit_id


@attr('fs')
class BasicTestCase(TestCase):
    """Mixin intended for data setup purposes (user, collection, etc...)

    """
    def setUp(self):
        """Define the test client and other test variables."""
        super().setUp()
        # expanding diffs in tests
        self.maxDiff = None

        # basic minimum test data
        deposit_request_types = {}
        # Add deposit request types
        for deposit_request_type in ['archive', 'metadata']:
            drt = DepositRequestType(name=deposit_request_type)
            drt.save()
            deposit_request_types[deposit_request_type] = drt

        _name = 'hal'
        _url = 'https://hal.archives-ouvertes.fr/'
        # set collection up
        _collection = DepositCollection(name=_name)
        _collection.save()
        # set user/client up
        _client = DepositClient.objects.create_user(username=_name,
                                                    password=_name,
                                                    url=_url)
        _client.collections = [_collection.id]
        _client.save()

        self.collection = _collection
        self.user = _client
        self.username = _name
        self.userpass = _name

        self.deposit_request_types = deposit_request_types

    def tearDown(self):
        super().tearDown()
        # Clean up uploaded files in temporary directory (tests have
        # their own media root folder)
        if os.path.exists(MEDIA_ROOT):
            for d in os.listdir(MEDIA_ROOT):
                shutil.rmtree(os.path.join(MEDIA_ROOT, d))


class WithAuthTestCase(TestCase):
    """Mixin intended for testing the api with basic authentication.

    """
    def setUp(self):
        super().setUp()
        _token = '%s:%s' % (self.username, self.userpass)
        token = base64.b64encode(_token.encode('utf-8'))
        authorization = 'Basic %s' % token.decode('utf-8')
        self.client.credentials(HTTP_AUTHORIZATION=authorization)

    def tearDown(self):
        super().tearDown()
        self.client.credentials()


class CommonCreationRoutine(TestCase):
    """Mixin class to share initialization routine.


    cf:
        `class`:test_deposit_update.DepositReplaceExistingDataTest
        `class`:test_deposit_update.DepositUpdateDepositWithNewDataTest
        `class`:test_deposit_update.DepositUpdateFailuresTest
        `class`:test_deposit_delete.DepositDeleteTest

    """
    def setUp(self):
        super().setUp()

        self.atom_entry_data0 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <external_identifier>some-external-id</external_identifier>
</entry>"""

        self.atom_entry_data1 = b"""<?xml version="1.0"?>
<entry xmlns="http://www.w3.org/2005/Atom">
    <external_identifier>anotherthing</external_identifier>
</entry>"""

    def create_deposit_with_status_rejected(self):
        url = reverse(COL_IRI, args=[self.collection.name])

        data = b'some data which is clearly not a zip file'
        md5sum = hashlib.md5(data).hexdigest()
        external_id = 'some-external-id-1'

        # when
        response = self.client.post(
            url,
            content_type='application/zip',  # as zip
            data=data,
            # + headers
            CONTENT_LENGTH=len(data),
            # other headers needs HTTP_ prefix to be taken into account
            HTTP_SLUG=external_id,
            HTTP_CONTENT_MD5=md5sum,
            HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
            HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']

        return deposit_id

    def create_simple_deposit_partial(self):
        """Create a simple deposit (1 request) in `partial` state and returns
        its new identifier.

        Returns:
            deposit id

        """
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0,
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS='true')

        assert response.status_code == status.HTTP_201_CREATED
        response_content = parse_xml(BytesIO(response.content))
        deposit_id = response_content[
            '{http://www.w3.org/2005/Atom}deposit_id']
        return deposit_id

    def _update_deposit_with_status(self, deposit_id, status_partial=False):
        """Add to a given deposit another archive and update its current
           status to `ready` (by default).

        Returns:
            deposit id

        """
        # when
        response = self.client.post(
            reverse(EDIT_SE_IRI, args=[self.collection.name, deposit_id]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data1,
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS=status_partial)

        # then
        assert response.status_code == status.HTTP_201_CREATED
        return deposit_id

    def create_deposit_ready(self):
        """Create a complex deposit (2 requests) in status `ready`.

        """
        deposit_id = self.create_simple_deposit_partial()
        deposit_id = self._update_deposit_with_status(deposit_id)
        return deposit_id

    def create_deposit_partial(self):
        """Create a complex deposit (2 requests) in status `partial`.

        """
        deposit_id = self.create_simple_deposit_partial()
        deposit_id = self._update_deposit_with_status(
            deposit_id, status_partial=True)
        return deposit_id
