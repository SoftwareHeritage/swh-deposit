# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest
from rest_framework.exceptions import AuthenticationFailed

from swh.deposit.auth import KeycloakBasicAuthentication
from swh.deposit.tests.conftest import TEST_USER

REQUEST_OBJECT = "request-unused"
PASSWORD = "some-deposit-pass"


@pytest.fixture
def backend_success(mock_keycloakopenidconnect_ok, deposit_config, db):
    """Backend whose connection to keycloak will systematically succeed."""
    return KeycloakBasicAuthentication()


@pytest.fixture
def backend_failure(mock_keycloakopenidconnect_ko, deposit_config):
    """Backend whose connection to keycloak will systematically fail."""
    return KeycloakBasicAuthentication()


def test_backend_authentication_refused(backend_failure):
    with pytest.raises(AuthenticationFailed):
        backend_failure.authenticate_credentials(
            TEST_USER["username"], PASSWORD, REQUEST_OBJECT
        )


def test_backend_authentication_db_misconfigured(backend_success):
    """Keycloak configured ok, backend db misconfigured (missing user), this raises"""
    with pytest.raises(AuthenticationFailed, match="Unknown"):
        backend_success.authenticate_credentials(
            TEST_USER["username"], PASSWORD, REQUEST_OBJECT
        )


def test_backend_authentication_user_inactive(backend_success, deposit_user):
    """Keycloak configured ok, backend db configured, user inactive, this raises"""
    deposit_user.is_active = False
    deposit_user.save()

    with pytest.raises(AuthenticationFailed, match="Deactivated"):
        backend_success.authenticate_credentials(
            deposit_user.username, PASSWORD, REQUEST_OBJECT
        )


def test_backend_authentication_ok(backend_success, deposit_user):
    """Keycloak configured ok, backend db configured ok, user logs in

    """
    user0, _ = backend_success.authenticate_credentials(
        deposit_user.username, PASSWORD, REQUEST_OBJECT
    )

    assert user0 is not None

    # A second authentication call should leverage the django cache feature.

    user1, _ = backend_success.authenticate_credentials(
        deposit_user.username, PASSWORD, REQUEST_OBJECT
    )
    assert user1 is not None

    assert user0 == user1, "Should have been retrieved from the cache"
