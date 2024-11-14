# Copyright (C) 2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Tuple

from rest_framework import status

from swh.deposit.api.common import APIGet
from swh.deposit.api.private import APIPrivateView
from swh.deposit.api.utils import DepositSerializer
from swh.deposit.models import Deposit
from swh.deposit.utils import get_releases


class APIReleases(APIPrivateView, APIGet):
    """Deposit request class to list releases related to a deposit.

    HTTP verbs supported: GET
    """

    def process_get(
        self, request, collection_name: str, deposit: Deposit
    ) -> Tuple[int, Any, str]:
        """Create a list of releases related to the ``deposit``.

        Args:
            request (Request):
            collection_name: Collection owning the deposit
            deposit: Deposit concerned by the reading

        Returns:
            Tuple status, a list of deposits as dicts (sorted by increasing date),
            content-type
        """
        releases = DepositSerializer(get_releases(deposit), many=True)
        return status.HTTP_200_OK, releases.data, "application/json"
