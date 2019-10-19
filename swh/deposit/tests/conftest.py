# Copyright (C) 2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest
import psycopg2

from django.db import connections
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from swh.scheduler.tests.conftest import *  # noqa


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
        for k, v in [('ENGINE', 'django.db.backends.postgresql'),
                     ('NAME', 'tests'),
                     ('USER', postgresql_proc.user),
                     ('HOST', postgresql_proc.host),
                     ('PORT', postgresql_proc.port),
        ]:
            settings.DATABASES['default'][k] = v
        print('after: %s' % settings.DATABASES)
        execute_sql('DROP DATABASE IF EXISTS %s' % db_name)
        execute_sql('CREATE DATABASE %s TEMPLATE template0' % db_name)

    project.app.signals.something = prepare_db







