# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from swh.core.config import SWHConfig

from .auth import login_required


def index(request):
    return HttpResponse('SWH Deposit API - WIP')


@login_required()
def clients(request):
    """List existing clients.

    """
    cs = User.objects.all()

    return HttpResponse('Clients: %s' % ','.join((str(c) for c in cs)))


@login_required()
def client(request, client_id):
    """List information about one client.

    """
    c = get_object_or_404(User, pk=client_id)
    return HttpResponse('Client {id: %s, name: %s}' % (c.id, c.username))


class SWHDepositAPI(SWHConfig):
    CONFIG_BASE_FILENAME = 'deposit/server'

    DEFAULT_CONFIG = {
        'max_upload_size': ('int', 209715200),
        'verbose': ('bool', False),
        'noop': ('bool', False),
    }

    def __init__(self, **config):
        self.config = self.parse_config_file()
        self.config.update(config)

    def service_document(self, request):
        context = {
            'max_upload_size': self.config['max_upload_size'],
            'verbose': self.config['verbose'],
            'noop': self.config['noop'],
        }
        return render(request, 'deposit/service_document.xml',
                      context, content_type='application/xml')
