# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Optional

from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from sentry_sdk import capture_exception

from swh.auth.django.models import OIDCUser
from swh.auth.django.utils import oidc_user_from_profile
from swh.auth.keycloak import (
    KeycloakError,
    KeycloakOpenIDConnect,
    keycloak_error_message,
)
from swh.deposit.models import DepositClient

from .errors import UNAUTHORIZED, make_error_response

logger = logging.getLogger(__name__)


OIDC_DEPOSIT_CLIENT_ID = "swh-deposit"
DEPOSIT_PERMISSION = "swh.deposit.api"


def convert_response(request, content):
    """Convert response from drf's basic authentication mechanism to a
       swh-deposit one.

        Args:
           request (Request): Use to build the response
           content (bytes): The drf's answer

        Returns:

            Response with the same status error as before, only the
            body is now an swh-deposit compliant one.

    """
    from json import loads

    content = loads(content.decode("utf-8"))
    detail = content.get("detail")
    if detail:
        verbose_description = "API is protected by basic authentication"
    else:
        detail = "API is protected by basic authentication"
        verbose_description = None

    response = make_error_response(
        request, UNAUTHORIZED, summary=detail, verbose_description=verbose_description
    )
    response["WWW-Authenticate"] = 'Basic realm=""'

    return response


class WrapBasicAuthenticationResponseMiddleware:
    """Middleware to capture potential authentication error and convert
       them to standard deposit response.

       This is to be installed in django's settings.py module.

    """

    def __init__(self, get_response):
        super().__init__()
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code is status.HTTP_401_UNAUTHORIZED:
            content_type = response.get("content-type")
            if content_type == "application/json":
                return convert_response(request, response.content)

        return response


class HasDepositPermission(BasePermission):
    """Allows access to authenticated users with the DEPOSIT_PERMISSION.

    """

    def has_permission(self, request, view):
        assert isinstance(request.user, DepositClient)
        return request.user.oidc_user.has_perm(DEPOSIT_PERMISSION)


class KeycloakBasicAuthentication(BasicAuthentication):
    """Keycloack authentication against username/password.

    Deposit users will continue sending `Basic authentication` queries to the deposit
    server. Transparently, the deposit server will stop authenticate itself the users.
    It will delegate the authentication queries to the keycloak instance.

    Technically, reuses :class:`rest_framework.BasicAuthentication` and overrides the
    func:`authenticate_credentials` method to discuss with keycloak.

    As an implementation detail, this also uses the django cache mechanism to avoid too
    many authentication request to keycloak.

    """

    _client: Optional[KeycloakOpenIDConnect] = None

    @property
    def client(self):
        if self._client is None:
            self._client = KeycloakOpenIDConnect.from_configfile(
                client_id=OIDC_DEPOSIT_CLIENT_ID
            )
        return self._client

    def _cache_key(self, user_id: str) -> str:
        """Internal key to use to store user id token.

        """
        return f"oidc_user_{self.client.realm_name}_{self.client.client_id}_{user_id}"

    def get_user(self, user_id: str) -> Optional[OIDCUser]:
        """Retrieve user from cache if any.

        """
        oidc_profile = cache.get(self._cache_key(user_id))
        if oidc_profile:
            try:
                return oidc_user_from_profile(self.client, oidc_profile)
            except Exception as e:
                logger.warning("Error during cache token retrieval: %s", e)
                capture_exception(e)
        return None

    def authenticate_credentials(self, user_id, password, request):
        """Authenticate the user_id/password against keycloak.

        Raises:
            AuthenticationFailed in case of authentication failure

        Returns:
            Tuple of deposit_client, None.

        """
        oidc_user = self.get_user(user_id)
        ttl: Optional[int] = None
        if not oidc_user:
            try:
                oidc_profile = self.client.login(user_id, password)
            except KeycloakError as e:
                logger.debug("KeycloakError: e: %s", e)
                error_msg = keycloak_error_message(e)
                raise AuthenticationFailed(error_msg)

            oidc_user = oidc_user_from_profile(self.client, oidc_profile)
            ttl = int(
                oidc_user.refresh_expires_at.timestamp() - timezone.now().timestamp()
            )

        # Making sure the associated deposit client is correctly configured in backend
        try:
            deposit_client = DepositClient.objects.get(username=user_id)
        except DepositClient.DoesNotExist:
            raise AuthenticationFailed(f"Unknown user {user_id}")

        if not deposit_client.is_active:
            raise AuthenticationFailed(f"Deactivated user {user_id}")

        deposit_client.oidc_user = oidc_user

        if ttl:
            # cache the oidc_profile user while it's valid
            cache.set(
                self._cache_key(user_id), oidc_profile, timeout=max(0, ttl),
            )

        return (deposit_client, None)
