# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import asyncio

from aiohttp import BasicAuth
from aiohttp.web import HTTPUnauthorized, HTTPForbidden, HTTPBadRequest


def parse_authorization(authorization_header):
    """Parse authorization header value.

    Returns:
        a user dict with key 'name' and 'password'.

    Raises:
        HttpBadRequest in case of wrong realm or wrong base64 token.

    """
    try:
        userpass = BasicAuth.decode(authorization_header)
    except ValueError:
        raise HTTPBadRequest(text='Only \'basic\' realm is supported')

    return dict(name=userpass.login, password=userpass.password)


def check_authorization(backend, user):
    """Check the user's authorized to access the resources.

    Returns:
        True if authorized, False otherwise.

    """
    user_data = backend.client_get(user['name'])
    if not user_data:
        return False

    # need to decrypt credential column
    credential = user_data['credential']

    return user['password'] == credential


@asyncio.coroutine
def middleware_basic_auth(app, handler):
    """Authentication middleware.

    """
    @asyncio.coroutine
    def __middleware_handler(request):
        try:
            authorization_header = request.headers.get('Authorization')
            if not authorization_header:
                return HTTPUnauthorized()
            user = parse_authorization(authorization_header)
            if check_authorization(app['backend'], user):
                return (yield from handler(request))
            return HTTPForbidden()
        except HTTPBadRequest:
            raise
        except Exception:
            app.logger.exception(
                'Error occurred in authentication middleware layer')
    return __middleware_handler
