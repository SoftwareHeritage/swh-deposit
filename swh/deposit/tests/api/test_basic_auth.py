# Copyright (C) 2017-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module to check at least one basic authentication works.

"""

from django.urls import reverse_lazy as reverse
import pytest

from swh.deposit.config import SD_IRI

from .test_service_document import check_response


@pytest.fixture()
def deposit_config(common_deposit_config):
    return {
        **common_deposit_config,
        "authentication_provider": "basic",
    }


def test_service_document_basic(basic_authenticated_client):
    """With authentication, service document list user's collection

    """
    url = reverse(SD_IRI)
    response = basic_authenticated_client.get(url)
    check_response(response, basic_authenticated_client.deposit_client.username)
