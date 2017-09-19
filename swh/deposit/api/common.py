# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

from django.http import HttpResponse
from rest_framework.views import APIView

from swh.core.config import SWHConfig


ACCEPT_PACKAGINGS = ['http://purl.org/net/sword/package/SimpleZip']
ACCEPT_CONTENT_TYPES = ['application/zip']


def index(req):
    return HttpResponse('SWH Deposit API - WIP')


class SWHView(SWHConfig):
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


class SWHAPIView(APIView):
    """Mixin intended as a based API view to enforce the basic
       authentication check

    """
    pass
