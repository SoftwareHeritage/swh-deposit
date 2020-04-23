# Copyright (C) 2017-2019 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.deposit import utils

from ...config import METADATA_TYPE, SWHDefaultConfig
from ...models import DepositRequest, Deposit

from rest_framework.permissions import AllowAny

from swh.deposit.api.common import SWHAPIView
from swh.deposit.errors import make_error_dict, NOT_FOUND


class DepositReadMixin:
    """Deposit Read mixin

    """

    def _deposit_requests(self, deposit, request_type):
        """Given a deposit, yields its associated deposit_request

        Args:
            deposit (Deposit): Deposit to list requests for
            request_type (str): 'archive' or 'metadata'

        Yields:
            deposit requests of type request_type associated to the deposit

        """
        if isinstance(deposit, int):
            deposit = Deposit.objects.get(pk=deposit)

        deposit_requests = DepositRequest.objects.filter(
            type=request_type, deposit=deposit
        ).order_by("id")

        for deposit_request in deposit_requests:
            yield deposit_request

    def _metadata_get(self, deposit):
        """Given a deposit, aggregate all metadata requests.

        Args:
            deposit (Deposit): The deposit instance to extract
            metadata from.

        Returns:
            metadata dict from the deposit.

        """
        metadata = (
            m.metadata
            for m in self._deposit_requests(deposit, request_type=METADATA_TYPE)
        )
        return utils.merge(*metadata)


class SWHPrivateAPIView(SWHDefaultConfig, SWHAPIView):
    """Mixin intended as private api (so no authentication) based API view
       (for the private ones).

    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def checks(self, req, collection_name, deposit_id=None):
        """Override default checks implementation to allow empty collection.

        """
        if deposit_id:
            try:
                Deposit.objects.get(pk=deposit_id)
            except Deposit.DoesNotExist:
                return make_error_dict(
                    NOT_FOUND, "Deposit with id %s does not exist" % deposit_id
                )

        headers = self._read_headers(req)
        checks = self.additional_checks(req, headers, collection_name, deposit_id)
        if "error" in checks:
            return checks

        return {"headers": headers}

    def get(
        self,
        request,
        collection_name=None,
        deposit_id=None,
        format=None,
        *args,
        **kwargs,
    ):
        return super().get(request, collection_name, deposit_id, format)

    def put(
        self,
        request,
        collection_name=None,
        deposit_id=None,
        format=None,
        *args,
        **kwargs,
    ):
        return super().put(request, collection_name, deposit_id, format)
