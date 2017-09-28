# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# Generated from:
# cd swh_deposit && \
#    python3 -m manage inspectdb


from django.contrib.postgres.fields import JSONField, ArrayField
from django.contrib.auth.models import User, UserManager
from django.db import models
from django.utils.timezone import now


class Dbversion(models.Model):
    """Db version

    """
    version = models.IntegerField(primary_key=True)
    release = models.DateTimeField(default=now, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'dbversion'

    def __str__(self):
        return str({
            'version': self.version,
            'release': self.release,
            'description': self.description
        })


"""Possible status"""
DEPOSIT_STATUS = [
    ('partial', 'partial'),
    ('expired', 'expired'),
    ('ready', 'ready'),
    ('injecting', 'injecting'),
    ('success', 'success'),
    ('failure', 'failure'),
]


"""Possible status and the detailed meaning."""
DEPOSIT_STATUS_DETAIL = {
    'partial': 'the deposit is new or partially received since it can be'
               ' done in multiple requests',
    'expired': 'deposit has been there too long and is now '
               'deemed ready to be garbage collected',
    'ready': 'deposit is fully received and ready for injection',
    'injecting': "injection is ongoing on swh's side",
    'success': 'Injection is successful',
    'failure': 'Injection is a failure',
}


class DepositClient(User):
    """Deposit client

    """
    collections = ArrayField(models.IntegerField(), null=True)
    objects = UserManager()

    class Meta:
        db_table = 'deposit_client'

    def __str__(self):
        return str({
            'id': self.id,
            'collections': self.collections,
            'username': super().username,
        })


class Deposit(models.Model):
    """Deposit reception table

    """
    id = models.BigAutoField(primary_key=True)

    # First deposit reception date
    reception_date = models.DateTimeField(auto_now_add=True)
    # Date when the deposit is deemed complete and ready for injection
    complete_date = models.DateTimeField(null=True)
    # collection concerned by the deposit
    collection = models.ForeignKey(
        'DepositCollection', models.DO_NOTHING)
    # Deposit's external identifier
    external_id = models.TextField()
    # Deposit client
    client = models.ForeignKey('DepositClient', models.DO_NOTHING)
    # SWH's injection result identifier
    swh_id = models.TextField(blank=True, null=True)
    # Deposit's status regarding injection
    status = models.TextField(
        choices=DEPOSIT_STATUS,
        default='partial')

    class Meta:
        db_table = 'deposit'

    def __str__(self):
        return str({
            'id': self.id,
            'reception_date': self.reception_date,
            'collection': self.collection.name,
            'external_id': self.external_id,
            'client': self.client.username,
            'status': self.status
        })


class DepositRequestType(models.Model):
    """Deposit request type made by clients (either archive or metadata)

    """
    id = models.BigAutoField(primary_key=True)
    name = models.TextField()

    class Meta:
        db_table = 'deposit_request_type'

    def __str__(self):
        return str({'id': self.id, 'name': self.name})


class DepositRequest(models.Model):
    """Deposit request associated to one deposit.

    """
    id = models.BigAutoField(primary_key=True)
    # Deposit concerned by the request
    deposit = models.ForeignKey(Deposit, models.DO_NOTHING)
    date = models.DateTimeField(auto_now_add=True)
    # Deposit request information on the data to inject
    metadata = JSONField(null=True)
    type = models.ForeignKey(
        'DepositRequestType', models.DO_NOTHING)

    class Meta:
        db_table = 'deposit_request'

    def __str__(self):
        from json import dumps
        return str({
            'id': self.id,
            'deposit': self.deposit,
            'metadata': dumps(self.metadata),
        })


class DepositCollection(models.Model):
    id = models.BigAutoField(primary_key=True)
    # Human readable name for the collection type e.g HAL, arXiv, etc...
    name = models.TextField()

    class Meta:
        db_table = 'deposit_collection'

    def __str__(self):
        return str({'id': self.id, 'name': self.name})
