# Copyright (C) 2018-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from rest_framework.fields import _UnvalidatedField
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework import serializers

from . import SWHPrivateAPIView
from ..converters import convert_status_detail
from ...models import Deposit


class DefaultPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"


class StatusDetailField(_UnvalidatedField):
    """status_detail field is a dict, we want a simple message instead.
       So, we reuse the convert_status_detail from deposit_status
       endpoint to that effect.

    """

    def to_representation(self, value):
        return convert_status_detail(value)


class DepositSerializer(serializers.ModelSerializer):
    status_detail = StatusDetailField()

    class Meta:
        model = Deposit
        fields = "__all__"


class DepositList(ListAPIView, SWHPrivateAPIView):
    """Deposit request class to list the deposit's status per page.

    HTTP verbs supported: GET

    """

    serializer_class = DepositSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        params = self.request.query_params
        exclude_like = params.get("exclude")
        if exclude_like:
            # sql injection: A priori, nothing to worry about, django does it for
            # queryset
            # https://docs.djangoproject.com/en/3.0/topics/security/#sql-injection-protection  # noqa
            # https://docs.djangoproject.com/en/2.2/topics/security/#sql-injection-protection  # noqa
            deposits = (
                Deposit.objects.all()
                .exclude(external_id__startswith=exclude_like)
                .order_by("id")
            )
        else:
            deposits = Deposit.objects.all().order_by("id")
        return deposits
