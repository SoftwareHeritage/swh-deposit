from django.http import HttpResponse
from django.template import loader
from django.http import Http404

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


def service_document(request):
    template = loader.get_template('deposit/service_document.xml')
    context = {
        'max_upload_size': 209715200,
        'verbose': False,
        'noop': False,
    }
    return HttpResponse(template.render(context, request),
                        content_type='application/xml')
