# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import django

from swh.objstorage import _STORAGE_CLASSES

try:
    from .objstorage import MockObjStorage
    _STORAGE_CLASSES['mock'] = MockObjStorage
except ImportError:
    raise ValueError('Development error - '
                     'Problem during setup for mock objstorage')

TEST_CONFIG = {
    'objstorage': {
        'cls': 'mock',
        'args': {}
    },
    'max_upload_size': 209715200,
    'verbose': False,
    'noop': False,
    'authentication': {
        'white-list': {
            'GET': ['/'],
        },
    },
}


def parse_config_file(base_filename=None, config_filename=None,
                      additional_configs=None, global_config=True):
    return TEST_CONFIG


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swh.web.settings.development")

from swh.deposit.auth import HttpBasicAuthMiddleware  # noqa
from swh.deposit.api.deposit import SWHDeposit  # noqa
from swh.deposit.api.service_document import SWHServiceDocument  # noqa

# monkey patch :\
SWHServiceDocument.parse_config_file = parse_config_file
SWHDeposit.parse_config_file = parse_config_file
HttpBasicAuthMiddleware.parse_config_file = parse_config_file

django.setup()
