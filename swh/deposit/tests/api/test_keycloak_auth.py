# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json

from django.urls import reverse_lazy as reverse
import pytest

from swh.auth.keycloak import KeycloakError
from swh.deposit.config import SD_IRI
from swh.deposit.tests.conftest import mock_keycloakopenidconnect


@pytest.fixture
def mock_keycloakopenidconnect_ko(mocker, keycloak_mock_auth_failure):
    error = {
        "error": "unknown_error",  # does not help much but that can happen
    }
    error_message = json.dumps(error).encode()
    keycloak_mock_auth_failure.login.side_effect = KeycloakError(
        error_message=error_message, response_code=401
    )
    return mock_keycloakopenidconnect(mocker, keycloak_mock_auth_failure)


def test_keycloak_failure_service_document(unauthorized_client):
    """With authentication failure without detail, exception is returned correctly

    """
    url = reverse(SD_IRI)
    response = unauthorized_client.get(url)
    assert response.status_code == 401
    assert b"unknown_error" in response.content
