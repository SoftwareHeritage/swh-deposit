# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import ListView
from swh.core.config import SWHConfig


def index(request):
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


class SWHServiceDocument(SWHView):
    def get(self, request, *args, **kwargs):
        context = {
            'max_upload_size': self.config['max_upload_size'],
            'verbose': self.config['verbose'],
            'noop': self.config['noop'],
        }
        return render(request, 'deposit/service_document.xml',
                      context, content_type='application/xml')


class SWHUser(ListView, SWHView):
    model = User

    def get(self, *args, **kwargs):
        if 'client_id' in kwargs:
            msg = 'Client '
            cs = self.get_queryset().filter(pk=kwargs['client_id'])
        else:
            msg = 'Clients'
            cs = self.get_queryset().all()
        return HttpResponse('%s: %s' % (msg, ','.join((str(c) for c in cs))))
