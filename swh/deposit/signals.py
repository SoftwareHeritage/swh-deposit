# Copyright (C) 2017-2019  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

"""Module in charge of defining some uncoupled actions on deposit.

   Typically, checking that the archives deposited are ok are not
   directly testing in the request/answer to avoid too long
   computations.

   So this is done in the deposit_on_status_ready_for_check callback.

"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Deposit
from .config import SWHDefaultConfig, DEPOSIT_STATUS_VERIFIED
from .config import DEPOSIT_STATUS_DEPOSITED


def schedule_task(scheduler, task):
    """Schedule the task and return its identifier

    Args:
        task (dict): Task to schedule

    Returns:
        The task identifier

    """
    tasks = scheduler.create_tasks([task])
    if tasks:
        created_task = tasks[0]
        return created_task['id']


@receiver(post_save, sender=Deposit)
def post_deposit_save(sender, instance, created, raw, using,
                      update_fields, **kwargs):
    """When a deposit is saved, check for the deposit's status change and
       schedule actions accordingly.

       When the status passes to deposited, schedule checks.
       When the status pass to ready, schedule loading.  Otherwise, do
       nothing.

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
    default_config = SWHDefaultConfig()
    if not default_config.config['checks']:
        return

    if instance.status not in {DEPOSIT_STATUS_DEPOSITED,
                               DEPOSIT_STATUS_VERIFIED}:
        return

    from django.urls import reverse
    from swh.scheduler.utils import create_oneshot_task_dict

    args = [instance.collection.name, instance.id]

    # In the following, we are checking the instance.*task_id are not already
    # populated because the `instance.save()` call will also trigger a call to
    # that very function.

    if (instance.status == DEPOSIT_STATUS_DEPOSITED and
       not instance.check_task_id):
        # schedule deposit's checks
        from swh.deposit.config import PRIVATE_CHECK_DEPOSIT
        check_url = reverse(PRIVATE_CHECK_DEPOSIT, args=args)
        task = create_oneshot_task_dict('check-deposit',
                                        deposit_check_url=check_url)
        check_task_id = schedule_task(default_config.scheduler, task)
        instance.check_task_id = check_task_id
        instance.save()

    elif (instance.status == DEPOSIT_STATUS_VERIFIED and
          not instance.load_task_id):
        # schedule deposit loading
        from swh.deposit.config import PRIVATE_GET_RAW_CONTENT
        from swh.deposit.config import PRIVATE_GET_DEPOSIT_METADATA
        from swh.deposit.config import PRIVATE_PUT_DEPOSIT
        archive_url = reverse(PRIVATE_GET_RAW_CONTENT, args=args)
        meta_url = reverse(PRIVATE_GET_DEPOSIT_METADATA, args=args)
        update_url = reverse(PRIVATE_PUT_DEPOSIT, args=args)

        task = create_oneshot_task_dict('load-deposit',
                                        archive_url=archive_url,
                                        deposit_meta_url=meta_url,
                                        deposit_update_url=update_url)

        load_task_id = schedule_task(default_config.scheduler, task)
        instance.load_task_id = load_task_id
        instance.save()
