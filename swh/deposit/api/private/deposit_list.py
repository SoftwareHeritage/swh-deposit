# Copyright (C) 2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework import serializers

from ..common import SWHPrivateAPIView
from ...models import Deposit


class DefaultPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'


class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ('id', 'reception_date', 'complete_date', 'status',
                  'collection', 'external_id', 'client',
                  'swh_id', 'swh_id_context',
                  'swh_anchor_id', 'swh_anchor_id_context',
                  'status', 'status_detail', 'parent')


class DepositList(ListAPIView, SWHPrivateAPIView):
    """Deposit request class to list the deposit's status per page.

    HTTP verbs supported: GET

    """
    queryset = Deposit.objects.all().order_by('id')
    serializer_class = DepositSerializer
    pagination_class = DefaultPagination
