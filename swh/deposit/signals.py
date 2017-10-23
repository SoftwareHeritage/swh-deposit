# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of defining some uncoupled actions on deposit.

   Typically, checking that the archives deposited are ok are not
   directly testing in the request/answer to avoid too long
   computations.

   So this is done in the deposit_on_status_ready_for_check callback.

"""

import zipfile

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DepositRequest
from .config import DEPOSIT_STATUS_READY, DEPOSIT_STATUS_REJECTED
from .config import DEPOSIT_STATUS_READY_FOR_CHECKS, ARCHIVE_TYPE


def checks(deposit_request):
    """Additional checks to execute on the deposit request's associated
       data (archive).

    Args:
        The deposit request whose archive we need to check

    Returns:
        True if we can at least read some content to the
        request's deposit associated archive. False otherwise.

    """
    if deposit_request.type.name != ARCHIVE_TYPE:  # no check for other types
        return True

    try:
        archive = deposit_request.archive
        zf = zipfile.ZipFile(archive.path)
        zf.infolist()
    except Exception as e:
        return False
    else:
        return True


@receiver(post_save, sender=DepositRequest)
def deposit_on_status_ready_for_check(sender, instance, created, raw, using,
                                      update_fields, **kwargs):
    """Check the status is ready for check.
    If so, try and check the associated archives.
    If not, move along.

    When
        Triggered when a deposit is saved.

    Args:
        sender (DepositRequest): The model class
        instance (DepositRequest): The actual instance being saved
        created (bool): True if a new record was created
        raw (bool): True if the model is saved exactly as presented
                    (i.e. when loading a fixture). One should not
                    query/modify other records in the database as the
                    database might not be in a consistent state yet
        using: The database alias being used
        update_fields: The set of fields to update as passed to
                       Model.save(), or None if update_fields wasn’t
                       passed to save()

    """
    if instance.deposit.status is not DEPOSIT_STATUS_READY_FOR_CHECKS:
        return

    if not checks(instance):
        instance.deposit.status = DEPOSIT_STATUS_REJECTED
    else:
        instance.deposit.status = DEPOSIT_STATUS_READY

    instance.deposit.save()
