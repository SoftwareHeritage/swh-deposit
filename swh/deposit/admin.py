# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.contrib import admin

from .models import Deposit, DepositCollection, DepositRequestType
from .models import DepositClient

admin.site.register(DepositClient)
admin.site.register(Deposit)
admin.site.register(DepositCollection)
admin.site.register(DepositRequestType)
