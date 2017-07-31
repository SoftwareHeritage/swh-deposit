# Generated from:
# cd swh_deposit && \
#    python3 -m manage inspectdb


from django.contrib.postgres.fields import JSONField
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


class Client(models.Model):
    """Deposit's client references.

    """
    id = models.BigAutoField(primary_key=True)
    # Human readable name for the client e.g hal, arXiv, etc...
    name = models.TextField()
    credential = models.BinaryField(blank=True, null=True)

    class Meta:
        db_table = 'client'


DEPOSIT_STATUS = [
    ('partial', 'partial'),      # the deposit is new or partially received
                                 # since it can be done in multiple requests
    ('expired', 'expired'),      # deposit has been there too long and is now
                                 # deemed ready to be garbage collected
    ('ready', 'ready'),          # deposit is fully received and ready for
                                 # injection
    ('injecting', 'injecting'),  # injection is ongoing on swh's side
    ('success', 'success'),      # injection successful
    ('failure', 'failure'),      # injection failure
]


class Deposit(models.Model):
    """Deposit reception table

    """
    id = models.BigAutoField(primary_key=True)

    # First deposit reception date
    reception_date = models.DateTimeField()
    # Date when the deposit is deemed complete and ready for injection
    complete_date = models.DateTimeField(null=True)
    # Deposit reception source type
    type = models.ForeignKey(
        'DepositType', models.DO_NOTHING, db_column='type')
    # Deposit's uniue external identifier
    external_id = models.TextField()
    # Deposit client
    client_id = models.BigIntegerField()
    # SWH's injection result identifier
    swh_id = models.TextField(blank=True, null=True)
    # Deposit's status regarding injection
    status = models.TextField(
        choices=DEPOSIT_STATUS,
        default='partial')

    class Meta:
        db_table = 'deposit'


class DepositRequest(models.Model):
    """Deposit request made by clients

    """

    id = models.BigAutoField(primary_key=True)
    # Deposit concerned by the request
    deposit = models.ForeignKey(Deposit, models.DO_NOTHING)
    # Deposit request information on the data to inject
    metadata = JSONField()

    class Meta:
        db_table = 'deposit_request'


class DepositType(models.Model):
    id = models.BigAutoField(primary_key=True)
    # Human readable name for the deposit type e.g HAL, arXiv, etc...
    name = models.TextField()

    class Meta:
        db_table = 'deposit_type'
