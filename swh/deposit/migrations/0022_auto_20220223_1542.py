# Copyright (C) 2022  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.db import migrations, models

from swh.deposit.config import DEPOSIT_STATUS_LOAD_SUCCESS
from swh.deposit.models import DEPOSIT_CODE, DEPOSIT_METADATA_ONLY, DEPOSIT_TYPES


def fill_deposit_type(apps, schema_editor):
    """Fill the new field metadata_only on existing data. This will mark metadata only
    deposits all deposits whose status is done, their complete date is exactly the
    reception date, and they have their swhid filled in.

    """
    Deposit = apps.get_model("deposit", "Deposit")
    for deposit in Deposit.objects.all():
        deposit.type = (
            DEPOSIT_METADATA_ONLY
            if (
                deposit.status == DEPOSIT_STATUS_LOAD_SUCCESS
                and deposit.complete_date == deposit.reception_date
                and deposit.complete_date is not None
                and deposit.swhid is not None
                and deposit.swhid_context is not None
            )
            else DEPOSIT_CODE
        )
        deposit.save()


class Migration(migrations.Migration):
    dependencies = [
        ("deposit", "0021_deposit_origin_url_20201124_1438"),
    ]

    operations = [
        migrations.AddField(
            model_name="deposit",
            name="type",
            field=models.CharField(
                choices=DEPOSIT_TYPES,
                default=DEPOSIT_CODE,
                max_length=4,
            ),
            preserve_default=False,
        ),
        # Migrate and make the operations possibly reversible
        migrations.RunPython(
            fill_deposit_type,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
