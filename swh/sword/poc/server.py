# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import asyncio
import aiohttp.web
import click
import json
import multidict

from swh.core import config
from swh.core.api_async import (SWHRemoteAPI, decode_request)


DEFAULT_CONFIG = {
    'host': ('str', '0.0.0.0'),
    'port': ('int', 5012),
}


def encode_data(data, **kwargs):
    return aiohttp.web.Response(
        body=json.dumps(data),
        headers=multidict.MultiDict({'Content-Type': 'application/json'}),
        **kwargs
    )


@asyncio.coroutine
def index(request):
    return aiohttp.web.Response(text='SWH SWORD Server')


@asyncio.coroutine
def hello(request):
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, %s\n" % name
    return aiohttp.web.Response(text=text)


@asyncio.coroutine
def service_document():
    pass


@asyncio.coroutine
def create_document():
    pass


@asyncio.coroutine
def update_document():
    pass


@asyncio.coroutine
def status_operation():
    pass


@asyncio.coroutine
def delete_document():
    raise ValueError('Not implemented')


def make_app(config, **kwargs):
    app = SWHRemoteAPI(**kwargs)
    app.router.add_route('GET', '/', index)
    app.router.add_route('GET', '/{name}', hello)
    app.router.add_route('GET', '/v1/software/', service_document)
    app.router.add_route('GET', '/v1/status/', status_operation)
    app.router.add_route('POST', '/v1/software/', create_document)
    app.router.add_route('PUT', '/v1/software/', update_document)
    app.router.add_route('DELETE', '/v1/software/', delete_document)
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
    c = config.read(config_path, DEFAULT_CONFIG)
    port = port if port else c['port']
    host = host if host else c['host']
    app = make_app(c, debug=bool(debug))
    aiohttp.web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    launch()
