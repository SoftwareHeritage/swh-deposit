# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import base64

from swh.core.config import SWHConfig

from django.contrib.auth import authenticate, login

from .errors import UNAUTHORIZED, make_error, make_error_response


def view_or_basicauth(view, request, test_func, realm="", *args, **kwargs):
    """This determine if the request has already provided proper
    http-authorization or not.  If it is, returns the view. Otherwise,
    respond with a 401.

    Note: Only basic realm is supported.

    """
    if test_func(request.user):
        # Already logged in, just return the view.
        return view(request, *args, **kwargs)

    # They are not logged in. See if they provided login credentials
    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2:
            # NOTE: Only support basic authentication
            if auth[0].lower() == "basic":
                authorization_token = base64.b64decode(auth[1]).decode('utf-8')
                uname, passwd = authorization_token.split(':', 1)
                user = authenticate(username=uname, password=passwd)
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        request.user = user
                        if test_func(request.user):
                            return view(request, *args, **kwargs)

    # Either they did not provide an authorization header or
    # something in the authorization attempt failed. Send a 401
    # back to them to ask them to authenticate.
    err = make_error(UNAUTHORIZED, 'Access to this api needs authentication')
    response = make_error_response(request, err['error'])
    response['WWW-Authenticate'] = 'Basic realm="%s"' % realm
    return response


class HttpBasicAuthMiddleware(SWHConfig):
    """Middleware to install or not the basic authentication layer
       according to swh's yaml configuration.

       Note: / is white-listed from authentication
    """
    CONFIG_BASE_FILENAME = 'deposit/server'

    DEFAULT_CONFIG = {
        'authentication': ('bool', True),
    }

    def __init__(self, get_response):
        super().__init__()
        self.get_response = get_response
        self.config = self.parse_config_file()

    def __call__(self, request):
        # white-list /
        if request.method == 'GET' and request.path == '/':
            return self.get_response(request)

        if self.config['authentication']:
            r = view_or_basicauth(view=self.get_response,
                                  request=request,
                                  test_func=lambda u: u.is_authenticated())
            return r
        return self.get_response(request)
