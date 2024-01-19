# Copyright (C) 2017-2022 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Optional

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from swh.deposit.config import METADATA_TYPE, APIConfig
from swh.deposit.models import Deposit, DepositRequest


class DepositReadMixin:
    """Deposit Read mixin"""

    def _deposit_requests(self, deposit: Deposit, request_type: str):
        """Given a deposit, yields its associated deposit_request

        Args:
            deposit: Deposit to list requests for
            request_type: 'archive' or 'metadata'

        Yields:
            deposit requests of type request_type associated to the deposit,
            most recent first

        """
        deposit_requests = DepositRequest.objects.filter(
            type=request_type, deposit=deposit
        ).order_by("-id")

        for deposit_request in deposit_requests:
            yield deposit_request

    def _metadata_get(self, deposit: Deposit) -> Optional[bytes]:
        """Retrieve the last non-empty raw metadata object for that deposit, if any

        Args:
            deposit: The deposit instance to extract metadata from

        """
        for deposit_request in self._deposit_requests(
            deposit, request_type=METADATA_TYPE
        ):
            if deposit_request.raw_metadata is not None:
                return deposit_request.raw_metadata

        return None


class APIPrivateView(APIConfig, APIView):
    """Mixin intended as private api (so no authentication) based API view
    (for the private ones).

    """

    def __init__(self):
        super().__init__()
        self.authentication_classes = ()
        self.permission_classes = (AllowAny,)

    def checks(self, req, collection_name, deposit=None):
        """Override default checks implementation to allow empty collection."""
        headers = self._read_headers(req)
        self.additional_checks(req, headers, collection_name, deposit)

        return {"headers": headers}

    def get(
        self,
        request,
        collection_name=None,
        deposit_id=None,
        *args,
        **kwargs,
    ):
        return super().get(request, collection_name, deposit_id)

    def put(
        self,
        request,
        collection_name=None,
        deposit_id=None,
        *args,
        **kwargs,
    ):
        return super().put(request, collection_name, deposit_id)
