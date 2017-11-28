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

import datetime

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DepositRequest
from .config import SWHDefaultConfig


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
    default_config = SWHDefaultConfig()
    if not default_config.config['checks']:
        return

    # Schedule oneshot task for checking archives
    from swh.deposit.config import PRIVATE_CHECK_DEPOSIT
    from django.core.urlresolvers import reverse

    args = [instance.deposit.collection.name, instance.deposit.id]
    archive_check_url = reverse(
        PRIVATE_CHECK_DEPOSIT, args=args)

    task = {
        'policy': 'oneshot',
        'type': 'swh-deposit-archive-checks',
        'next_run': datetime.datetime.now(tz=datetime.timezone.utc),
        'arguments': {
            'args': [],
            'kwargs': {
                'archive_check_url': archive_check_url,
            },
        }
    }

    default_config.scheduler.create_tasks([task])
