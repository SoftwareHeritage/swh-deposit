# Copyright (C) 2017-2020  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

# Generated from:
# cd swh_deposit && \
#    python3 -m manage inspectdb

import datetime

from django.contrib.postgres.fields import JSONField, ArrayField
from django.contrib.auth.models import User, UserManager
from django.db import models
from django.utils.timezone import now

from .config import (
    DEPOSIT_STATUS_VERIFIED,
    DEPOSIT_STATUS_DEPOSITED,
    DEPOSIT_STATUS_PARTIAL,
    DEPOSIT_STATUS_LOAD_SUCCESS,
    DEPOSIT_STATUS_LOAD_FAILURE,
    DEPOSIT_STATUS_REJECTED,
    ARCHIVE_TYPE,
    METADATA_TYPE,
)


class Dbversion(models.Model):
    """Db version

    """

    version = models.IntegerField(primary_key=True)
    release = models.DateTimeField(default=now, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "dbversion"

    def __str__(self):
        return str(
            {
                "version": self.version,
                "release": self.release,
                "description": self.description,
            }
        )


"""Possible status"""
DEPOSIT_STATUS = [
    (DEPOSIT_STATUS_PARTIAL, DEPOSIT_STATUS_PARTIAL),
    ("expired", "expired"),
    (DEPOSIT_STATUS_DEPOSITED, DEPOSIT_STATUS_DEPOSITED),
    (DEPOSIT_STATUS_VERIFIED, DEPOSIT_STATUS_VERIFIED),
    (DEPOSIT_STATUS_REJECTED, DEPOSIT_STATUS_REJECTED),
    ("loading", "loading"),
    (DEPOSIT_STATUS_LOAD_SUCCESS, DEPOSIT_STATUS_LOAD_SUCCESS),
    (DEPOSIT_STATUS_LOAD_FAILURE, DEPOSIT_STATUS_LOAD_FAILURE),
]


"""Possible status and the detailed meaning."""
DEPOSIT_STATUS_DETAIL = {
    DEPOSIT_STATUS_PARTIAL: "Deposit is partially received. To finalize it, "
    "In-Progress header should be false",
    "expired": "Deposit has been there too long and is now "
    "deemed ready to be garbage collected",
    DEPOSIT_STATUS_DEPOSITED: "Deposit is ready for additional checks "
    "(tarball ok, metadata, etc...)",
    DEPOSIT_STATUS_VERIFIED: "Deposit is fully received, checked, and "
    "ready for loading",
    DEPOSIT_STATUS_REJECTED: "Deposit failed the checks",
    "loading": "Loading is ongoing on swh's side",
    DEPOSIT_STATUS_LOAD_SUCCESS: "The deposit has been successfully "
    "loaded into the Software Heritage archive",
    DEPOSIT_STATUS_LOAD_FAILURE: "The deposit loading into the "
    "Software Heritage archive failed",
}


class DepositClient(User):
    """Deposit client

    """

    collections = ArrayField(models.IntegerField(), null=True)
    objects = UserManager()  # type: ignore
    # this typing hint is due to a mypy/django-stubs limitation,
    # see https://github.com/typeddjango/django-stubs/issues/174

    provider_url = models.TextField(null=False)
    domain = models.TextField(null=False)

    class Meta:
        db_table = "deposit_client"

    def __str__(self):
        return str(
            {
                "id": self.id,
                "collections": self.collections,
                "username": super().username,
                "domain": self.domain,
                "provider_url": self.provider_url,
            }
        )


class Deposit(models.Model):
    """Deposit reception table

    """

    id = models.BigAutoField(primary_key=True)

    # First deposit reception date
    reception_date = models.DateTimeField(auto_now_add=True)
    # Date when the deposit is deemed complete and ready for loading
    complete_date = models.DateTimeField(null=True)
    # collection concerned by the deposit
    collection = models.ForeignKey("DepositCollection", models.DO_NOTHING)
    # Deposit's external identifier
    external_id = models.TextField()
    # Deposit client
    client = models.ForeignKey("DepositClient", models.DO_NOTHING)
    # SWH's loading result identifier
    swh_id = models.TextField(blank=True, null=True)
    swh_id_context = models.TextField(blank=True, null=True)
    # Deposit's status regarding loading
    status = models.TextField(choices=DEPOSIT_STATUS, default=DEPOSIT_STATUS_PARTIAL)
    status_detail = JSONField(null=True)
    # deposit can have one parent
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True)
    check_task_id = models.TextField(
        blank=True, null=True, verbose_name="Scheduler's associated checking task id"
    )
    load_task_id = models.TextField(
        blank=True, null=True, verbose_name="Scheduler's associated loading task id"
    )

    class Meta:
        db_table = "deposit"

    def __str__(self):
        d = {
            "id": self.id,
            "reception_date": self.reception_date,
            "collection": self.collection.name,
            "external_id": self.external_id,
            "client": self.client.username,
            "status": self.status,
        }

        if self.status in (DEPOSIT_STATUS_REJECTED):
            d["status_detail"] = self.status_detail
        return str(d)

    @property
    def origin_url(self):
        return "%s/%s" % (self.client.provider_url.rstrip("/"), self.external_id)


def client_directory_path(instance: "DepositRequest", filename: str) -> str:
    """Callable to determine the upload archive path. This defaults to
     MEDIA_ROOT/client_<user_id>/%Y%m%d-%H%M%S.%f/<filename>.

    The format "%Y%m%d-%H%M%S.%f" is the reception date of the associated deposit
    formatted using strftime.

    Args:
        instance: DepositRequest concerned by the upload
        filename: Filename of the uploaded file

    Returns:
        The upload archive path.

    """
    reception_date = instance.deposit.reception_date
    assert isinstance(reception_date, datetime.datetime)
    folder = reception_date.strftime("%Y%m%d-%H%M%S.%f")
    return f"client_{instance.deposit.client.id}/{folder}/{filename}"


REQUEST_TYPES = [(ARCHIVE_TYPE, ARCHIVE_TYPE), (METADATA_TYPE, METADATA_TYPE)]


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
    raw_metadata = models.TextField(null=True)
    # this can be null when type is 'metadata'
    archive = models.FileField(null=True, upload_to=client_directory_path)

    type = models.CharField(max_length=8, choices=REQUEST_TYPES, null=True)

    class Meta:
        db_table = "deposit_request"

    def __str__(self):
        meta = None
        if self.metadata:
            from json import dumps

            meta = dumps(self.metadata)

        archive_name = None
        if self.archive:
            archive_name = self.archive.name

        return str(
            {
                "id": self.id,
                "deposit": self.deposit,
                "metadata": meta,
                "archive": archive_name,
            }
        )


class DepositCollection(models.Model):
    id = models.BigAutoField(primary_key=True)
    # Human readable name for the collection type e.g HAL, arXiv, etc...
    name = models.TextField()

    class Meta:
        db_table = "deposit_collection"

    def __str__(self):
        return str({"id": self.id, "name": self.name})
