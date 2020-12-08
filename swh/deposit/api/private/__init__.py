# Copyright (C) 2017-2020 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict, List, Tuple

from rest_framework.permissions import AllowAny

from swh.deposit import utils
from swh.deposit.api.common import AuthenticatedAPIView

from ...config import METADATA_TYPE, APIConfig
from ...models import Deposit, DepositRequest


class DepositReadMixin:
    """Deposit Read mixin

    """

    def _deposit_requests(self, deposit: Deposit, request_type: str):
        """Given a deposit, yields its associated deposit_request

        Args:
            deposit: Deposit to list requests for
            request_type: 'archive' or 'metadata'

        Yields:
            deposit requests of type request_type associated to the deposit

        """
        deposit_requests = DepositRequest.objects.filter(
            type=request_type, deposit=deposit
        ).order_by("id")

        for deposit_request in deposit_requests:
            yield deposit_request

    def _metadata_get(self, deposit: Deposit) -> Tuple[Dict[str, Any], List[str]]:
        """Given a deposit, retrieve all metadata requests into one Dict and returns both that
           aggregated metadata dict and the list of raw_metdadata.

        Args:
            deposit: The deposit instance to extract metadata from

        Returns:
            Tuple of aggregated metadata dict, list of raw_metadata

        """
        metadata: List[Dict[str, Any]] = []
        raw_metadata: List[str] = []
        for deposit_request in self._deposit_requests(
            deposit, request_type=METADATA_TYPE
        ):
            metadata.append(deposit_request.metadata)
            raw_metadata.append(deposit_request.raw_metadata)

        aggregated_metadata = utils.merge(*metadata)
        return (aggregated_metadata, raw_metadata)


class APIPrivateView(APIConfig, AuthenticatedAPIView):
    """Mixin intended as private api (so no authentication) based API view
       (for the private ones).

    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def checks(self, req, collection_name, deposit=None):
        """Override default checks implementation to allow empty collection.

        """
        headers = self._read_headers(req)
        self.additional_checks(req, headers, collection_name, deposit)

        return {"headers": headers}

    def get(
        self, request, collection_name=None, deposit_id=None, *args, **kwargs,
    ):
        return super().get(request, collection_name, deposit_id)

    def put(
        self, request, collection_name=None, deposit_id=None, *args, **kwargs,
    ):
        return super().put(request, collection_name, deposit_id)
