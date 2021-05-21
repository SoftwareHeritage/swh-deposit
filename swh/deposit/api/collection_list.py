# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.shortcuts import render
from rest_framework import status
from rest_framework.generics import ListAPIView

from swh.deposit.api.common import APIBase
from swh.deposit.api.utils import DefaultPagination, DepositSerializer
from swh.deposit.models import Deposit


class CollectionListAPI(ListAPIView, APIBase):
    """Deposit request class to list the user deposits.

    HTTP verbs supported: ``GET``

    """

    serializer_class = DepositSerializer
    pagination_class = DefaultPagination

    def get(self, request, *args, **kwargs):
        """List the user's collection if the user has access to said collection.

        """
        self.checks(request, kwargs["collection_name"])
        paginated_result = super().get(request, *args, **kwargs)
        data = paginated_result.data
        # Build pagination link headers
        links = []
        for link_name in ["next", "previous"]:
            link = data.get(link_name)
            if link is None:
                continue
            links.append(f'<{link}>; rel="{link_name}"')
        response = render(
            request,
            "deposit/collection_list.xml",
            context={
                "count": data["count"],
                "results": [dict(d) for d in data["results"]],
            },
            content_type="application/xml",
            status=status.HTTP_200_OK,
        )
        response._headers["Link"] = ",".join(links)
        return response

    def get_queryset(self):
        """List the deposits for the authenticated user (pagination is handled by the
        `pagination_class` class attribute).

        """
        return Deposit.objects.filter(client=self.request.user.id).order_by("id")
