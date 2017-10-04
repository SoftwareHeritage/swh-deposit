# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import django


TEST_CONFIG = {
    'objstorage': {
        'cls': 'in-memory',
        'args': {}
    },
    'max_upload_size': 209715200,
    'verbose': False,
    'noop': False,
    'authentication': {
        'activated': 'true',
        'white-list': {
            'GET': ['/'],
        },
    },
}


def parse_config_file(base_filename=None, config_filename=None,
                      additional_configs=None, global_config=True):
    return TEST_CONFIG


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swh.web.settings.development")

from swh.deposit.config import SWHDefaultConfig  # noqa

# monkey patch this class method permits to override, for tests
# purposes, the default configuration without side-effect, i.e do not
# load the configuration from disk
SWHDefaultConfig.parse_config_file = parse_config_file

django.setup()
