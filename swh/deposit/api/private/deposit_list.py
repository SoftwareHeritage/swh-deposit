# Copyright (C) 2018-2022  The Software Heritage developers
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

    def paginate_queryset(self, queryset):
        """Return a single page of results. This enriches the queryset results with
        metadata if any.

        """
        page_result = self.paginator.paginate_queryset(
            queryset, self.request, view=self
        )

        deposits = []
        for deposit in page_result:
            deposit_requests = deposit.depositrequest_set.filter(
                type="metadata"
            ).order_by("-id")
            # enrich deposit with raw metadata when we have some
            if deposit_requests and len(deposit_requests) > 0:
                raw_meta = deposit_requests[0].raw_metadata
                if raw_meta:
                    deposit.set_raw_metadata(raw_meta)

            deposits.append(deposit)

        return deposits

    def get_queryset(self):
        """Retrieve queryset of deposits (with some optional filtering)."""
        params = self.request.query_params
        exclude_like = params.get("exclude")
        username = params.get("username")

        if username:
            deposits_qs = Deposit.objects.select_related("client").filter(
                client__username=username
            )
        else:
            deposits_qs = Deposit.objects.all()

        if exclude_like:
            # sql injection: A priori, nothing to worry about, django does it for
            # queryset
            # https://docs.djangoproject.com/en/3.0/topics/security/#sql-injection-protection  # noqa
            deposits_qs = deposits_qs.exclude(external_id__startswith=exclude_like)

        return deposits_qs.order_by("id")
