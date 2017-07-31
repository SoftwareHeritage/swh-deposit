from django.http import HttpResponse
from django.template import loader
from django.http import Http404

from swh.core.config import SWHConfig

from .models import Client


def index(request):
    return HttpResponse('SWH Deposit API - WIP')


def clients(request):
    """List existing clients.

    """
    cs = Client.objects.all()

    return HttpResponse('Clients: %s' % ','.join((str(c) for c in cs)))


def client(request, client_id):
    """List information about one client.

    """
    c = Client.objects.filter(pk=client_id).all()
    if len(c) <= 0:
        raise Http404('Client with id %s not found' % client_id)

    c = c[0]
    return HttpResponse('Client {id: %s, name: %s}' % (c.id, c.name))


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
        template = loader.get_template('deposit/service_document.xml')
        context = {
            'max_upload_size': self.config['max_upload_size'],
            'verbose': self.config['verbose'],
            'noop': self.config['noop'],
        }
        return HttpResponse(template.render(context, request),
                            content_type='application/xml')
