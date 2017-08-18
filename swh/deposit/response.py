from django.http import HttpResponse

import xml


class XmlResponse(HttpResponse):
    """
    An HTTP response class that consumes data to be serialized to XML.

    :param data: Data to be dumped into json. By default only ``dict`` objects
      are allowed to be passed due to a security flaw before EcmaScript 5. See
      the ``safe`` parameter for more information.
    :param encoder: Should be an xml encoder class. Defaults to
      ``django.core.serializers.xml.DjangoJSONEncoder``.
    :param safe: Controls if only ``dict`` objects may be serialized. Defaults
      to ``True``.
    :param xml_dumps_params: A dictionary of kwargs passed to xml.dumps().
    """

    def __init__(self, data, safe=True,
                 xml_dumps_params=None, **kwargs):
        if safe and not isinstance(data, dict):
            raise TypeError(
                'In order to allow non-dict objects to be serialized set the '
                'safe parameter to False.'
            )
        if xml_dumps_params is None:
            xml_dumps_params = {}
        kwargs.setdefault('content_type', 'application/xml')
        data = xml.dumps(data, **xml_dumps_params)
        super(XmlResponse, self).__init__(content=data, **kwargs)
