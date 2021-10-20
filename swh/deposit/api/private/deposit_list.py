# Copyright (C) 2018-2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from rest_framework.generics import ListAPIView

from swh.deposit.api.utils import DefaultPagination, DepositSerializer

from . import APIPrivateView
from ...models import Deposit


class APIList(ListAPIView, APIPrivateView):
    """Deposit request class to list the deposit's status per page.

    HTTP verbs supported: GET

    """

    serializer_class = DepositSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        params = self.request.query_params
        exclude_like = params.get("exclude")
        username = params.get("username")

        if username:
            deposits = Deposit.objects.select_related("client").filter(
                client__username=username
            )
        else:
            deposits = Deposit.objects.all()

        if exclude_like:
            # sql injection: A priori, nothing to worry about, django does it for
            # queryset
            # https://docs.djangoproject.com/en/3.0/topics/security/#sql-injection-protection  # noqa
            deposits = deposits.exclude(external_id__startswith=exclude_like)
        return deposits.order_by("id")
