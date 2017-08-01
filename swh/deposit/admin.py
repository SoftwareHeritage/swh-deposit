from django.contrib import admin

from .models import Client, DepositType, Deposit, DepositRequest

admin.site.register(Client)
admin.site.register(DepositType)
admin.site.register(Deposit)
admin.site.register(DepositRequest)
