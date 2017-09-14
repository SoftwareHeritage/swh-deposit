# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.http import HttpResponse
from django.views import View

from swh.core.config import SWHConfig


ACCEPT_PACKAGINGS = ['http://purl.org/net/sword/package/SimpleZip']
ACCEPT_CONTENT_TYPES = ['application/zip']


def index(req):
    return HttpResponse('SWH Deposit API - WIP')


class SWHView(SWHConfig, View):
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
