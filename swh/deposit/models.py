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

from .config import DEPOSIT_STATUS_READY, DEPOSIT_STATUS_READY_FOR_CHECKS
from .config import DEPOSIT_STATUS_PARTIAL


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
    (DEPOSIT_STATUS_PARTIAL, DEPOSIT_STATUS_PARTIAL),
    ('expired', 'expired'),
    (DEPOSIT_STATUS_READY_FOR_CHECKS, DEPOSIT_STATUS_READY_FOR_CHECKS),
    (DEPOSIT_STATUS_READY, DEPOSIT_STATUS_READY),
    ('rejected', 'rejected'),
    ('injecting', 'injecting'),
    ('success', 'success'),
    ('failure', 'failure'),
]


"""Possible status and the detailed meaning."""
DEPOSIT_STATUS_DETAIL = {
    DEPOSIT_STATUS_PARTIAL: 'Deposit is new or partially received since it can'
                            ' be done in multiple requests',
    'expired': 'Deposit has been there too long and is now '
               'deemed ready to be garbage collected',
    DEPOSIT_STATUS_READY_FOR_CHECKS: 'Deposit is ready for additional checks '
                                     '(tarball ok, etc...)',
    DEPOSIT_STATUS_READY: 'Deposit is fully received, checked, and '
                          'ready for injection',
    'rejected': 'Deposit failed the checks',
    'injecting': "Injection is ongoing on swh's side",
    'success': 'Injection is successful',
    'failure': 'Injection is a failure',
}


class DepositClient(User):
    """Deposit client

    """
    collections = ArrayField(models.IntegerField(), null=True)
    objects = UserManager()
    url = models.TextField(null=False)

    class Meta:
        db_table = 'deposit_client'

    def __str__(self):
        return str({
            'id': self.id,
            'collections': self.collections,
            'username': super().username,
        })


def format_swh_id(collection_name, revision_id):
    """Format swh_id value before storing in swh-deposit backend.

    Args:
        collection_name (str): the collection's name
        revision_id (str): the revision's hash identifier

    Returns:
        The identifier as string

    """
    return 'swh-%s-%s' % (collection_name, revision_id)


def previous_revision_id(swh_id):
    """Compute the parent's revision id (if any) from the swh_id.

    Args:
        swh_id (id): SWH Identifier from a previous deposit.

    Returns:
        None if no parent revision is detected.
        The revision id's hash if any.

    """
    if swh_id:
        return swh_id.split('-')[2]
    return None


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
        default=DEPOSIT_STATUS_PARTIAL)

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


def client_directory_path(instance, filename):
    """Callable to upload archive in MEDIA_ROOT/user_<id>/<filename>

    Args:
        instance (DepositRequest): DepositRequest concerned by the upload
        filename (str): Filename of the uploaded file

    Returns:
        A path to be prefixed by the MEDIA_ROOT to access physically
        to the file uploaded.

    """
    return 'client_{0}/{1}'.format(instance.deposit.client.id, filename)


class DepositRequest(models.Model):
    """Deposit request associated to one deposit.

    """
    id = models.BigAutoField(primary_key=True)
    # Deposit concerned by the request
    deposit = models.ForeignKey(Deposit, models.DO_NOTHING)
    date = models.DateTimeField(auto_now_add=True)
    # Deposit request information on the data to inject
    # this can be null when type is 'archive'
    metadata = JSONField(null=True)
    # this can be null when type is 'metadata'
    archive = models.FileField(null=True, upload_to=client_directory_path)

    type = models.ForeignKey(
        'DepositRequestType', models.DO_NOTHING)

    class Meta:
        db_table = 'deposit_request'

    def __str__(self):
        meta = None
        if self.metadata:
            from json import dumps
            meta = dumps(self.metadata)

        archive_name = None
        if self.archive:
            archive_name = self.archive.name

        return str({
            'id': self.id,
            'deposit': self.deposit,
            'metadata': meta,
            'archive': archive_name
        })


class DepositCollection(models.Model):
    id = models.BigAutoField(primary_key=True)
    # Human readable name for the collection type e.g HAL, arXiv, etc...
    name = models.TextField()

    class Meta:
        db_table = 'deposit_collection'

    def __str__(self):
        return str({'id': self.id, 'name': self.name})
