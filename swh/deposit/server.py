# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import asyncio
import aiohttp.web
import click
import jinja2

from swh.core import config
from swh.core.config import SWHConfig
from swh.core.api_async import SWHRemoteAPI


DEFAULT_CONFIG_SERVER = {
    'host': ('str', '0.0.0.0'),
    'port': ('int', 5012),
}


def encode_data(data, template_name=None, **kwargs):
    return aiohttp.web.Response(
        body=data,
        headers={'Content-Type': 'application/xml'},
        **kwargs
    )


class DepositWebServer(SWHConfig):
    """Base class to define endpoints route.

    """

    CONFIG_BASE_FILENAME = 'deposit/server'

    DEFAULT_CONFIG = {
        'max_upload_size': ('int', 200 * 1024 * 1024),
    }

    def __init__(self, config=None):
        if config:
            self.config = config
        else:
            self.config = self.parse_config_file()
        template_loader = jinja2.FileSystemLoader(
            searchpath=["swh/deposit/templates"])
        self.template_env = jinja2.Environment(loader=template_loader)

    @asyncio.coroutine
    def index(self, request):
        return aiohttp.web.Response(text='SWH Deposit Server')

    @asyncio.coroutine
    def service_document(self, request):
        tpl = self.template_env.get_template('service_document.xml')
        output = tpl.render(
            noop=True, verbose=False, max_upload_size=200*1024*1024)
        return encode_data(data=output)

    @asyncio.coroutine
    def create_document(self, request):
        pass

    @asyncio.coroutine
    def update_document(self, request):
        pass

    @asyncio.coroutine
    def status_operation(self, request):
        pass

    @asyncio.coroutine
    def delete_document(self, request):
        raise ValueError('Not implemented')


def make_app(config, **kwargs):
    app = SWHRemoteAPI(**kwargs)
    server = DepositWebServer()
    app.router.add_route('GET',    '/', server.index)
    app.router.add_route('GET',    '/api/1/deposit/', server.service_document)
    app.router.add_route('GET',    '/api/1/status/', server.status_operation)
    app.router.add_route('POST',   '/api/1/deposit/', server.create_document)
    app.router.add_route('PUT',    '/api/1/deposit/', server.update_document)
    app.router.add_route('DELETE', '/api/1/deposit/', server.delete_document)
    app.update(config)
    return app


@click.command()
@click.argument('config-path', required=1)
@click.option('--host', default='0.0.0.0', help="Host to run the server")
@click.option('--port', default=5012, type=click.INT,
              help="Binding port of the server")
@click.option('--debug/--nodebug', default=True,
              help="Indicates if the server should run in debug mode")
def launch(config_path, host, port, debug):
    cfg = config.read(config_path, DEFAULT_CONFIG_SERVER)
    port = port if port else cfg['port']
    host = host if host else cfg['host']
    app = make_app(cfg, debug=bool(debug))
    aiohttp.web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    launch()
