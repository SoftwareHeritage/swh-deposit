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

from .models import Deposit, DepositRequest, DepositRequestType
from .config import DEPOSIT_STATUS_READY, DEPOSIT_STATUS_REJECTED
from .config import DEPOSIT_STATUS_READY_FOR_CHECKS


def checks(deposit):
    """Additional checks to execute on the deposit's associated data (archive).
       the status to ready for injection.

    Args:
        The deposit whose archives we need to check

    Returns:
        True if every we can at least read some content to every
        deposit associated archive. False otherwise.

    """
    archive_type = DepositRequestType.objects.filter(name='archive')
    requests = DepositRequest.objects.filter(deposit=deposit,
                                             type=archive_type)

    try:
        for req in requests:
            archive = req.archive
            print('check %s' % archive.path)
            zf = zipfile.ZipFile(archive.path)
            zf.infolist()
    except Exception as e:
        print(e)
        return False
    else:
        return True


@receiver(post_save, sender=Deposit)
def deposit_on_status_ready_for_check(sender, instance, created, raw, using,
                                      update_fields, **kwargs):
    """Check the status is ready for check.
    If so, try and check the associated archives.
    If not, move along.

    When
        Triggered when a deposit is saved.

    Args:
        sender (Deposit): The model class
        instance (Deposit): The actual instance being saved
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
    if instance.status is not DEPOSIT_STATUS_READY_FOR_CHECKS:
        return
    if not checks(instance):
        instance.status = DEPOSIT_STATUS_REJECTED
    else:
        instance.status = DEPOSIT_STATUS_READY
        print('Check ok: %s -> %s' % (instance.status, DEPOSIT_STATUS_READY))

    instance.save()
