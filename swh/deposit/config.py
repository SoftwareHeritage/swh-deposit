# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import os
import logging

from swh.core.config import SWHConfig

# IRIs (Internationalized Resource identifier) sword 2.0 specified
EDIT_SE_IRI = 'edit_se_iri'
EM_IRI = 'em_iri'
CONT_FILE_IRI = 'cont_file_iri'
SD_IRI = 'servicedocument'
COL_IRI = 'upload'
STATE_IRI = 'state_iri'
PRIVATE_GET_RAW_CONTENT = 'private-download'
PRIVATE_PUT_DEPOSIT = 'private-update'
PRIVATE_GET_DEPOSIT_METADATA = 'private-read'

ARCHIVE_KEY = 'archive'
METADATA_KEY = 'metadata'

AUTHORIZED_PLATFORMS = ['development', 'production', 'testing']


def setup_django_for(platform):
    """Setup function for command line tools (swh.deposit.create_user,
       swh.deposit.scheduler.cli) to initialize the needed db access.

    Note:
        Do not import any django related module prior to this function
        call. Otherwise, this will raise an
        django.core.exceptions.ImproperlyConfigured error message.

    Args:
        platform (str): the platform the scheduling is running

    Raises:
        ValueError in case of wrong platform inputs.

    """
    if platform not in AUTHORIZED_PLATFORMS:
        raise ValueError('Platform should be one of %s' % AUTHORIZED_PLATFORMS)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'swh.deposit.settings.%s' % platform)

    import django
    django.setup()


class SWHDefaultConfig(SWHConfig):
    """Mixin intended to enrich views with SWH configuration.

    """
    CONFIG_BASE_FILENAME = 'deposit/server'

    DEFAULT_CONFIG = {
        'max_upload_size': ('int', 209715200),
    }

    def __init__(self, **config):
        super().__init__()
        self.config = self.parse_config_file()
        self.config.update(config)
        self.log = logging.getLogger('swh.deposit')
