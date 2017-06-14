# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import base64
import hashlib
import os
import shutil
import tarfile
import tempfile

from django.core.urlresolvers import reverse
from django.test import TestCase
from io import BytesIO
import pytest
from rest_framework import status

from swh.deposit.config import (COL_IRI, EM_IRI, EDIT_SE_IRI,
                                DEPOSIT_STATUS_PARTIAL,
                                DEPOSIT_STATUS_VERIFIED,
                                DEPOSIT_STATUS_REJECTED,
                                DEPOSIT_STATUS_DEPOSITED)
from swh.deposit.models import DepositClient, DepositCollection, Deposit
from swh.deposit.models import DepositRequest
from swh.deposit.models import DepositRequestType
from swh.deposit.parsers import parse_xml
from swh.deposit.settings.testing import MEDIA_ROOT
from swh.core import tarball


def compute_info(archive_path):
    """Given a path, compute information on path.

    """
    with open(archive_path, 'rb') as f:
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
        'dir': os.path.dirname(archive_path),
        'name': os.path.basename(archive_path),
        'path': archive_path,
        'length': length,
        'sha1sum': sha1sum.hexdigest(),
        'md5sum': md5sum.hexdigest(),
        'data': data
    }


def _compress(path, extension, dir_path):
    """Compress path according to extension

    """
    if extension == 'zip' or extension == 'tar':
        return tarball.compress(path, extension, dir_path)
    elif '.' in extension:
        split_ext = extension.split('.')
        if split_ext[0] != 'tar':
            raise ValueError(
                'Development error, only zip or tar archive supported, '
                '%s not supported' % extension)

        # deal with specific tar
        mode = split_ext[1]
        supported_mode = ['xz', 'gz', 'bz2']
        if mode not in supported_mode:
            raise ValueError(
                'Development error, only %s supported, %s not supported' % (
                    supported_mode, mode))
        files = tarball._ls(dir_path)
        with tarfile.open(path, 'w:%s' % mode) as t:
            for fpath, fname in files:
                t.add(fpath, arcname=fname, recursive=False)

        return path


def create_arborescence_archive(root_path, archive_name, filename, content,
                                up_to_size=None, extension='zip'):
    """Build an archive named archive_name in the root_path.
    This archive contains one file named filename with the content content.

    Args:
        root_path (str): Location path of the archive to create
        archive_name (str): Archive's name (without extension)
        filename (str): Archive's content is only one filename
        content (bytes): Content of the filename
        up_to_size (int | None): Fill in the blanks size to oversize
          or complete an archive's size
        extension (str): Extension of the archive to write (default is zip)

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
    _length = len(content)
    count = 0
    batch_size = 128
    with open(filepath, 'wb') as f:
        f.write(content)
        if up_to_size:  # fill with blank content up to a given size
            count += _length
            while count < up_to_size:
                f.write(b'0'*batch_size)
                count += batch_size

    _path = '%s.%s' % (dir_path, extension)
    _path = _compress(_path, extension, dir_path)
    return compute_info(_path)


def create_archive_with_archive(root_path, name, archive):
    """Create an archive holding another.

    """
    invalid_archive_path = os.path.join(root_path, name)
    with tarfile.open(invalid_archive_path, 'w:gz') as _archive:
        _archive.add(archive['path'], arcname=archive['name'])
    return compute_info(invalid_archive_path)


@pytest.mark.fs
class FileSystemCreationRoutine(TestCase):
    """Mixin intended for tests needed to tamper with archives.

    """
    def setUp(self):
        """Define the test client and other test variables."""
        super().setUp()
        self.root_path = '/tmp/swh-deposit/test/build-zip/'
        os.makedirs(self.root_path, exist_ok=True)

        self.archive = create_arborescence_archive(
            self.root_path, 'archive1', 'file1', b'some content in file')

        self.atom_entry = b"""<?xml version="1.0"?>
            <entry xmlns="http://www.w3.org/2005/Atom">
                <title>Awesome Compiler</title>
                <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
                <external_identifier>1785io25c695</external_identifier>
                <updated>2017-10-07T15:17:08Z</updated>
                <author>some awesome author</author>
                <url>https://hal-test.archives-ouvertes.fr</url>
        </entry>"""

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.root_path)

    def create_simple_binary_deposit(self, status_partial=True):
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_content = parse_xml(BytesIO(response.content))
        _status = response_content['deposit_status']
        if status_partial:
            expected_status = DEPOSIT_STATUS_PARTIAL
        else:
            expected_status = DEPOSIT_STATUS_VERIFIED
        self.assertEqual(_status, expected_status)
        deposit_id = int(response_content['deposit_id'])
        return deposit_id

    def create_complex_binary_deposit(self, status_partial=False):
        deposit_id = self.create_simple_binary_deposit(
            status_partial=True)

        # Add a second archive to the deposit
        # update its status to DEPOSIT_STATUS_VERIFIED
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
        deposit_id = int(response_content['deposit_id'])
        return deposit_id

    def create_deposit_archive_with_archive(self, archive_extension):
        # we create the holding archive to a given extension
        archive = create_arborescence_archive(
            self.root_path, 'archive1', 'file1', b'some content in file',
            extension=archive_extension)

        # now we create an archive holding the first created archive
        invalid_archive = create_archive_with_archive(
            self.root_path, 'invalid.tar.gz', archive)

        # we deposit it
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/x-tar',
            data=invalid_archive['data'],
            CONTENT_LENGTH=invalid_archive['length'],
            HTTP_MD5SUM=invalid_archive['md5sum'],
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS=False,
            HTTP_CONTENT_DISPOSITION='attachment; filename=%s' % (
                invalid_archive['name'], ))

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_content = parse_xml(BytesIO(response.content))
        _status = response_content['deposit_status']
        self.assertEqual(_status, DEPOSIT_STATUS_DEPOSITED)
        deposit_id = int(response_content['deposit_id'])
        return deposit_id

    def update_binary_deposit(self, deposit_id, status_partial=False):
        # update existing deposit with atom entry metadata
        response = self.client.post(
            reverse(EDIT_SE_IRI, args=[self.collection.name, deposit_id]),
            content_type='application/atom+xml;type=entry',
            data=self.codemeta_entry_data1,
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS=status_partial)

        # then
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_content = parse_xml(BytesIO(response.content))
        _status = response_content['deposit_status']
        if status_partial:
            expected_status = DEPOSIT_STATUS_PARTIAL
        else:
            expected_status = DEPOSIT_STATUS_DEPOSITED
        self.assertEqual(_status, expected_status)
        deposit_id = int(response_content['deposit_id'])
        return deposit_id


@pytest.mark.fs
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
        _provider_url = 'https://hal-test.archives-ouvertes.fr/'
        _domain = 'archives-ouvertes.fr/'
        # set collection up
        _collection = DepositCollection(name=_name)
        _collection.save()
        # set user/client up
        _client = DepositClient.objects.create_user(username=_name,
                                                    password=_name,
                                                    provider_url=_provider_url,
                                                    domain=_domain)
        _client.collections = [_collection.id]
        _client.last_name = _name
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
            <url>https://hal-test.archives-ouvertes.fr/some-external-id</url>
            <author>some awesome author</author>
        </entry>"""

        self.atom_entry_data1 = b"""<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom">
            <author>another one</author>
            <author>no one</author>
        </entry>"""

        self.atom_entry_data2 = b"""<?xml version="1.0"?>
            <entry xmlns="http://www.w3.org/2005/Atom">
                <title>Awesome Compiler</title>
                <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
                <external_identifier>1785io25c695</external_identifier>
                <updated>2017-10-07T15:17:08Z</updated>
                <author>some awesome author</author>
                <url>https://hal-test.archives-ouvertes.fr/id</url>
        </entry>"""

        self.codemeta_entry_data0 = b"""<?xml version="1.0"?>
            <entry xmlns="http://www.w3.org/2005/Atom"
                xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
                <title>Awesome Compiler</title>
                <url>https://hal-test.archives-ouvertes.fr/1785io25c695</url>
                <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>
                <external_identifier>1785io25c695</external_identifier>
                <updated>2017-10-07T15:17:08Z</updated>
                <author>some awesome author</author>
                <codemeta:description>description</codemeta:description>
                <codemeta:keywords>key-word 1</codemeta:keywords>
        </entry>"""

        self.codemeta_entry_data1 = b"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom"
xmlns:codemeta="https://doi.org/10.5063/SCHEMA/CODEMETA-2.0">
  <title>Composing a Web of Audio Applications</title>
  <client>hal</client>
  <id>hal-01243065</id>
  <external_identifier>hal-01243065</external_identifier>
  <codemeta:url>https://hal-test.archives-ouvertes.fr/hal-01243065</codemeta:url>
  <codemeta:applicationCategory>test</codemeta:applicationCategory>
  <codemeta:keywords>DSP programming,Web</codemeta:keywords>
  <codemeta:dateCreated>2017-05-03T16:08:47+02:00</codemeta:dateCreated>
  <codemeta:description>this is the description</codemeta:description>
  <codemeta:version>1</codemeta:version>
  <codemeta:runtimePlatform>phpstorm</codemeta:runtimePlatform>
  <codemeta:developmentStatus>stable</codemeta:developmentStatus>
  <codemeta:programmingLanguage>php</codemeta:programmingLanguage>
  <codemeta:programmingLanguage>python</codemeta:programmingLanguage>
  <codemeta:programmingLanguage>C</codemeta:programmingLanguage>
  <codemeta:license>
    <codemeta:name>GNU General Public License v3.0 only</codemeta:name>
  </codemeta:license>
  <codemeta:license>
    <codemeta:name>CeCILL Free Software License Agreement v1.1</codemeta:name>
  </codemeta:license>
  <author>
    <name>HAL</name>
    <email>hal@ccsd.cnrs.fr</email>
  </author>
  <codemeta:author>
    <codemeta:name>Morane Gruenpeter</codemeta:name>
  </codemeta:author>
</entry>"""

    def create_deposit_with_invalid_archive(self,
                                            external_id='some-external-id-1'):
        url = reverse(COL_IRI, args=[self.collection.name])

        data = b'some data which is clearly not a zip file'
        md5sum = hashlib.md5(data).hexdigest()

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
        deposit_id = int(response_content['deposit_id'])
        return deposit_id

    def create_deposit_with_status(
            self, status,
            external_id='some-external-id-1',
            swh_id=None,
            swh_id_context=None,
            swh_anchor_id=None,
            swh_anchor_id_context=None,
            status_detail=None):
        # create an invalid deposit which we will update further down the line
        deposit_id = self.create_deposit_with_invalid_archive(external_id)

        # We cannot create some form of deposit with a given status in
        # test context ('rejected' for example). Update in place the
        # deposit with such status to permit some further tests.
        deposit = Deposit.objects.get(pk=deposit_id)
        if status == DEPOSIT_STATUS_REJECTED:
            deposit.status_detail = status_detail
        deposit.status = status
        if swh_id:
            deposit.swh_id = swh_id
        if swh_id_context:
            deposit.swh_id_context = swh_id_context
        if swh_anchor_id:
            deposit.swh_anchor_id = swh_anchor_id
        if swh_anchor_id_context:
            deposit.swh_anchor_id_context = swh_anchor_id_context
        deposit.save()
        return deposit_id

    def create_simple_deposit_partial(self, external_id='some-external-id'):
        """Create a simple deposit (1 request) in `partial` state and returns
        its new identifier.

        Returns:
            deposit id

        """
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/atom+xml;type=entry',
            data=self.atom_entry_data0,
            HTTP_SLUG=external_id,
            HTTP_IN_PROGRESS='true')

        assert response.status_code == status.HTTP_201_CREATED
        response_content = parse_xml(BytesIO(response.content))
        deposit_id = int(response_content['deposit_id'])
        return deposit_id

    def create_deposit_partial_with_data_in_args(self, data):
        """Create a simple deposit (1 request) in `partial` state with the data
        or metadata as an argument and returns  its new identifier.

        Args:
            data: atom entry

        Returns:
            deposit id

        """
        response = self.client.post(
            reverse(COL_IRI, args=[self.collection.name]),
            content_type='application/atom+xml;type=entry',
            data=data,
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS='true')

        assert response.status_code == status.HTTP_201_CREATED
        response_content = parse_xml(BytesIO(response.content))
        deposit_id = int(response_content['deposit_id'])
        return deposit_id

    def _update_deposit_with_status(self, deposit_id, status_partial=False):
        """Add to a given deposit another archive and update its current
           status to `deposited` (by default).

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

    def create_deposit_ready(self, external_id='some-external-id'):
        """Create a complex deposit (2 requests) in status `deposited`.

        """
        deposit_id = self.create_simple_deposit_partial(
            external_id=external_id)
        deposit_id = self._update_deposit_with_status(deposit_id)
        return deposit_id

    def create_deposit_partial(self, external_id='some-external-id'):
        """Create a complex deposit (2 requests) in status `partial`.

        """
        deposit_id = self.create_simple_deposit_partial(
            external_id=external_id)
        deposit_id = self._update_deposit_with_status(
            deposit_id, status_partial=True)
        return deposit_id

    def add_metadata_to_deposit(self, deposit_id, status_partial=False):
        """Add metadata to deposit.

        """
        # when
        response = self.client.post(
            reverse(EDIT_SE_IRI, args=[self.collection.name, deposit_id]),
            content_type='application/atom+xml;type=entry',
            data=self.codemeta_entry_data1,
            HTTP_SLUG='external-id',
            HTTP_IN_PROGRESS=status_partial)
        assert response.status_code == status.HTTP_201_CREATED
        # then
        deposit = Deposit.objects.get(pk=deposit_id)
        assert deposit is not None

        deposit_requests = DepositRequest.objects.filter(deposit=deposit)
        assert deposit_requests is not []

        for dr in deposit_requests:
            if dr.type.name == 'metadata':
                assert deposit_requests[0].metadata is not {}
        return deposit_id
