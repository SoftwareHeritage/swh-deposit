# Copyright (C) 2018-2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict
from xml.etree import ElementTree

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import CharField, Q, TextField
from django.http import JsonResponse
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
import sentry_sdk

from swh.deposit.api.private import APIPrivateView
from swh.deposit.api.utils import DefaultPagination, DepositSerializer
from swh.deposit.models import Deposit
from swh.deposit.utils import parse_swh_deposit_origin, parse_swh_metadata_provenance
from swh.model.swhids import QualifiedSWHID


def _enrich_deposit_with_metadata(deposit: Deposit) -> Deposit:
    deposit_requests = deposit.depositrequest_set.filter(type="metadata")
    deposit_requests = deposit_requests.order_by("-id")
    # enrich deposit with raw metadata when we have some
    if deposit_requests and len(deposit_requests) > 0:
        raw_meta = deposit_requests[0].raw_metadata
        if raw_meta:
            deposit.set_raw_metadata(raw_meta)
    return deposit


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
            _enrich_deposit_with_metadata(deposit)
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


def _deposit_search_query(search_value: str) -> Q:
    fields = [f for f in Deposit._meta.fields if isinstance(f, (CharField, TextField))]
    queries = [Q(**{f.name + "__icontains": search_value}) for f in fields]
    search_query = Q()
    for query in queries:
        search_query = search_query | query
    return search_query


@api_view()
@authentication_classes([])
@permission_classes([AllowAny])
def deposit_list_datatables(request: Request) -> JsonResponse:
    """Special API view to list and filter deposits, produced responses are intended
    to be consumed by datatables js framework used in deposits admin Web UI."""
    table_data: Dict[str, Any] = {}
    table_data["draw"] = int(request.GET.get("draw", 1))
    try:
        username = request.GET.get("username")
        if username:
            deposits = Deposit.objects.select_related("client").filter(
                client__username=username
            )
        else:
            deposits = Deposit.objects.all()

        deposits_count = deposits.count()
        search_value = request.GET.get("search[value]")
        if search_value:
            deposits = deposits.filter(_deposit_search_query(search_value))

        exclude_pattern = request.GET.get("excludePattern")
        if exclude_pattern:
            deposits = deposits.exclude(_deposit_search_query(exclude_pattern))

        column_order = request.GET.get("order[0][column]")
        field_order = request.GET.get("columns[%s][name]" % column_order, "id")
        order_dir = request.GET.get("order[0][dir]", "desc")

        if order_dir == "desc":
            field_order = "-" + field_order

        deposits = deposits.order_by(field_order)

        length = int(request.GET.get("length", 10))
        page = int(request.GET.get("start", 0)) // length + 1
        paginator = Paginator(deposits, length)

        data = [
            DepositSerializer(_enrich_deposit_with_metadata(d)).data
            for d in paginator.page(page).object_list
        ]

        table_data["recordsTotal"] = deposits_count
        table_data["recordsFiltered"] = deposits.count()
        data_list = []
        for d in data:
            data_dict = {
                "id": d["id"],
                "type": d["type"],
                "external_id": d["external_id"],
                "raw_metadata": d["raw_metadata"],
                "reception_date": d["reception_date"],
                "status": d["status"],
                "status_detail": d["status_detail"],
                "swhid": d["swhid"],
                "swhid_context": d["swhid_context"],
            }
            provenance = None
            raw_metadata = d["raw_metadata"]
            # for meta deposit, the uri should be the url provenance
            if raw_metadata and d["type"] == "meta":  # metadata provenance
                provenance = parse_swh_metadata_provenance(
                    ElementTree.fromstring(raw_metadata)
                )
            # For code deposits the uri is the origin
            # First, trying to determine it out of the raw metadata associated with the
            # deposit
            elif raw_metadata and d["type"] == "code":
                create_origin_url, add_to_origin_url = parse_swh_deposit_origin(
                    ElementTree.fromstring(raw_metadata)
                )
                provenance = create_origin_url or add_to_origin_url

            # For code deposits, if not provided, use the origin_url
            if not provenance and d["type"] == "code":
                if d["origin_url"]:
                    provenance = d["origin_url"]

                # If still not found, fallback using the swhid context
                if not provenance and d["swhid_context"]:
                    swhid = QualifiedSWHID.from_string(d["swhid_context"])
                    provenance = swhid.origin

            data_dict["uri"] = provenance  # could be None

            data_list.append(data_dict)

        table_data["data"] = data_list

    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        table_data["error"] = (
            "An error occurred while retrieving the list of deposits !"
        )
        if settings.DEBUG:
            table_data["error"] += "\n" + str(exc)

    return JsonResponse(table_data)
