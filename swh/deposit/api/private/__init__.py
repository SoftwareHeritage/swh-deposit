# Copyright (C) 2017-2018 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.deposit import utils

from ...config import METADATA_TYPE
from ...models import DepositRequest, Deposit


class DepositReadMixin:
    """Deposit Read mixin

    """

    def _deposit_requests(self, deposit, request_type):
        """Given a deposit, yields its associated deposit_request

        Args:
            deposit (Deposit): Deposit to list requests for
            request_type (str): Archive or metadata type

        Yields:
            deposit requests of type request_type associated to the deposit

        """
        if isinstance(deposit, int):
            deposit = Deposit.objects.get(pk=deposit)

        deposit_requests = DepositRequest.objects.filter(
            type=self.deposit_request_types[request_type],
            deposit=deposit).order_by('id')

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
        metadata = (m.metadata for m in self._deposit_requests(
            deposit, request_type=METADATA_TYPE))
        return utils.merge(*metadata)
