# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import base64
import pytest
import psycopg2

from django.urls import reverse
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from rest_framework import status
from rest_framework.test import APIClient

# , STATE_IRI,
from swh.scheduler.tests.conftest import *  # noqa

from swh.deposit.config import (
    COL_IRI, EDIT_SE_IRI, DEPOSIT_STATUS_DEPOSITED, DEPOSIT_STATUS_REJECTED,
    DEPOSIT_STATUS_PARTIAL, DEPOSIT_STATUS_LOAD_SUCCESS
)
from swh.deposit.tests.common import create_arborescence_archive


TEST_USER = {
    'username': 'test',
    'password': 'password',
    'email': 'test@example.org',
    'provider_url': 'https://hal-test.archives-ouvertes.fr/',
    'domain': 'archives-ouvertes.fr/',
    'collection': {
        'name': 'test'
    },
}


def execute_sql(sql):
    """Execute sql to postgres db"""
    with psycopg2.connect(database='postgres') as conn:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(sql)


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config, parser, args):
    """This hook is done prior to django loading.
       Used to initialize the deposit's server db.

    """
    import project.app.signals

    def prepare_db(*args, **kwargs):
        from django.conf import settings
        db_name = 'tests'
        print('before: %s' % settings.DATABASES)
        # work around db settings for django
        for k, v in [
                ('ENGINE', 'django.db.backends.postgresql'),
                ('NAME', 'tests'),
                ('USER', postgresql_proc.user),  # noqa
                ('HOST', postgresql_proc.host),  # noqa
                ('PORT', postgresql_proc.port),  # noqa
        ]:
            settings.DATABASES['default'][k] = v

        print('after: %s' % settings.DATABASES)
        execute_sql('DROP DATABASE IF EXISTS %s' % db_name)
        execute_sql('CREATE DATABASE %s TEMPLATE template0' % db_name)

    project.app.signals.something = prepare_db


@pytest.fixture
def deposit_collection(db):
    from swh.deposit.models import DepositCollection
    collection_name = TEST_USER['collection']['name']
    try:
        collection = DepositCollection._default_manager.get(
            name=collection_name)
    except DepositCollection.DoesNotExist:
        collection = DepositCollection(name=collection_name)
        collection.save()
    return collection


@pytest.fixture
def deposit_user(db, deposit_collection):
    """Create/Return the test_user "test"

    """
    from swh.deposit.models import DepositClient
    try:
        user = DepositClient._default_manager.get(
            username=TEST_USER['username'])
    except DepositClient.DoesNotExist:
        user = DepositClient._default_manager.create_user(
            username=TEST_USER['username'],
            email=TEST_USER['email'],
            password=TEST_USER['password'],
            provider_url=TEST_USER['provider_url'],
            domain=TEST_USER['domain'],
        )
        user.collections = [deposit_collection.id]
        user.save()
    return user


@pytest.fixture
def client():
    """Override pytest-django one which does not work for djangorestframework.

    """
    return APIClient()  # <- drf's client


@pytest.yield_fixture
def authenticated_client(client, deposit_user):
    """Returned a logged client

    """
    _token = '%s:%s' % (deposit_user.username, TEST_USER['password'])
    token = base64.b64encode(_token.encode('utf-8'))
    authorization = 'Basic %s' % token.decode('utf-8')
    client.credentials(HTTP_AUTHORIZATION=authorization)
    yield client
    client.logout()


@pytest.fixture
def sample_archive(tmp_path):
    """Returns a sample archive

    """
    tmp_path = str(tmp_path)  # pytest version limitation in previous version
    archive = create_arborescence_archive(
        tmp_path, 'archive1', 'file1', b'some content in file')

    return archive


def create_deposit(
        authenticated_client, collection_name: str, sample_archive,
        external_id: str):
    """Create a skeleton shell deposit

    """
    url = reverse(COL_IRI, args=[collection_name])
    # when
    response = authenticated_client.post(
        url,
        content_type='application/zip',  # as zip
        data=sample_archive['data'],
        # + headers
        CONTENT_LENGTH=sample_archive['length'],
        HTTP_SLUG=external_id,
        HTTP_CONTENT_MD5=sample_archive['md5sum'],
        HTTP_PACKAGING='http://purl.org/net/sword/package/SimpleZip',
        HTTP_IN_PROGRESS='false',
        HTTP_CONTENT_DISPOSITION='attachment; filename=filename0')

    # then
    assert response.status_code == status.HTTP_201_CREATED
    from swh.deposit.models import Deposit
    deposit = Deposit._default_manager.get(external_id=external_id)
    return deposit


@pytest.fixture
def deposited_deposit(
        sample_archive, deposit_collection, authenticated_client):
    """Returns a deposit with status 'deposited'.

    """
    deposit = create_deposit(
        authenticated_client, deposit_collection.name, sample_archive,
        external_id='external-id-deposited')
    assert deposit.status == DEPOSIT_STATUS_DEPOSITED
    return deposit


@pytest.fixture
def rejected_deposit(sample_archive, deposit_collection, authenticated_client):
    """Returns a deposit with status 'rejected'.

    """
    deposit = create_deposit(
        authenticated_client, deposit_collection.name, sample_archive,
        external_id='external-id-rejected')
    deposit.status = DEPOSIT_STATUS_REJECTED
    deposit.save()
    assert deposit.status == DEPOSIT_STATUS_REJECTED
    return deposit


@pytest.fixture
def partial_deposit(sample_archive, deposit_collection, authenticated_client):
    """Returns a deposit with status 'partial'.

    """
    deposit = create_deposit(
        authenticated_client, deposit_collection.name, sample_archive,
        external_id='external-id-partial'
    )
    deposit.status = DEPOSIT_STATUS_PARTIAL
    deposit.save()
    assert deposit.status == DEPOSIT_STATUS_PARTIAL
    return deposit


@pytest.fixture
def partial_deposit_with_metadata(
        sample_archive, deposit_collection, authenticated_client,
        atom_dataset):
    """Returns deposit with archive and metadata provided, status 'partial'

    """
    # deposit with one archive
    deposit = create_deposit(
        authenticated_client, deposit_collection.name, sample_archive,
        external_id='external-id-partial'
    )
    deposit.status = DEPOSIT_STATUS_PARTIAL
    deposit.save()
    assert deposit.status == DEPOSIT_STATUS_PARTIAL

    # update the deposit with metadata
    response = authenticated_client.post(
        reverse(EDIT_SE_IRI, args=[deposit_collection.name, deposit.id]),
        content_type='application/atom+xml;type=entry',
        data=atom_dataset['entry-data0'] % deposit.external_id.encode('utf-8'),
        HTTP_SLUG=deposit.external_id,
        HTTP_IN_PROGRESS='true')

    assert response.status_code == status.HTTP_201_CREATED
    assert deposit.status == DEPOSIT_STATUS_PARTIAL
    return deposit


@pytest.fixture
def complete_deposit(sample_archive, deposit_collection, authenticated_client):
    """Returns a completed deposit (load success)

    """
    deposit = create_deposit(
        authenticated_client, deposit_collection.name, sample_archive,
        external_id='external-id-complete'
    )
    deposit.status = DEPOSIT_STATUS_LOAD_SUCCESS
    _swh_id_context = 'https://hal.archives-ouvertes.fr/hal-01727745'
    deposit.swh_id = 'swh:1:dir:42a13fc721c8716ff695d0d62fc851d641f3a12b'
    deposit.swh_id_context = '%s;%s' % (
        deposit.swh_id, _swh_id_context)
    deposit.swh_anchor_id = \
        'swh:rev:1:548b3c0a2bb43e1fca191e24b5803ff6b3bc7c10'
    deposit.swh_anchor_id_context = '%s;%s' % (
        deposit.swh_anchor_id, _swh_id_context)
    deposit.save()
    return deposit
