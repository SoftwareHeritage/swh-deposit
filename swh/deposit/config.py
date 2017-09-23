# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

from swh.core.config import SWHConfig

# IRIs (Internationalized Resource identifier) sword 2.0 specified
EDIT_SE_IRI = 'edit_se_iri'
EM_IRI = 'em_iri'
CONT_FILE_IRI = 'cont_file_iri'
SD_IRI = 'servicedocument'
COL_IRI = 'upload'
STATE_IRI = 'status'


class SWHDefaultConfig(SWHConfig):
    """Mixin intended to enrich views with SWH configuration.

    """
    CONFIG_BASE_FILENAME = 'deposit/server'

    DEFAULT_CONFIG = {
        'max_upload_size': ('int', 209715200),
        'verbose': ('bool', False),
        'noop': ('bool', False),
    }

    def __init__(self, **config):
        super().__init__()
        self.config = self.parse_config_file()
        self.config.update(config)
        self.log = logging.getLogger('swh.deposit')
