# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import base64
import pytest
import psycopg2

from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from rest_framework.test import APIClient

from swh.scheduler.tests.conftest import *  # noqa


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
def deposit_user(db):
    """Create/Return the test_user "test"

    """
    from swh.deposit.models import DepositCollection, DepositClient
    # UserModel = django_user_model
    collection_name = TEST_USER['collection']['name']
    try:
        collection = DepositCollection._default_manager.get(
            name=collection_name)
    except DepositCollection.DoesNotExist:
        collection = DepositCollection(name=collection_name)
        collection.save()

    # Create a user
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
        user.collections = [collection.id]
        user.save()

    return user


# @pytest.fixture
# def headers(deposit_user):
    import base64
    _token = '%s:%s' % (deposit_user.username, TEST_USER['password'])
    token = base64.b64encode(_token.encode('utf-8'))
    authorization = 'Basic %s' % token.decode('utf-8')
    return {
        'AUTHENTICATION': authorization,
    }


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
