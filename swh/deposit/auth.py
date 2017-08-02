# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import base64

from django.http import HttpResponse
from django.contrib.auth import authenticate, login


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
    response = HttpResponse()
    response.status_code = 401
    response['WWW-Authenticate'] = 'Basic realm="%s"' % realm
    return response


def login_required(realm=""):
    """A simple decorator that requires a user to be logged in.

    If they are not logged in the request is examined for a
    'authorization' header.

    If the header is present it is tested for basic authentication and
    the user is logged in with the provided credentials.

    If the header is not present a http 401 is sent back to the
    requestor to provide credentials.

    Use is simple:
    ```
    @login_required()
    def view:
       pass
    ```

    You can provide the name of the realm to ask for
    authentication within.

    """
    def view_decorator(func):
        def wrapper(request, *args, **kwargs):
            return view_or_basicauth(func, request,
                                     lambda u: u.is_authenticated(),
                                     realm, *args, **kwargs)
        return wrapper
    return view_decorator
