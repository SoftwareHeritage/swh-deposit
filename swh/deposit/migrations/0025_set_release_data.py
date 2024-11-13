# Copyright (C) 2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

from swh.deposit.config import DEPOSIT_STATUS_LOAD_SUCCESS
from swh.deposit.models import DEPOSIT_CODE
from swh.deposit.utils import extract_release_data


def set_release_data(apps: Apps, schema_editor: BaseDatabaseSchemaEditor):
    Deposit = apps.get_model("deposit", "Deposit")
    for deposit in Deposit.objects.filter(
        status=DEPOSIT_STATUS_LOAD_SUCCESS, type=DEPOSIT_CODE
    ):
        release_data = extract_release_data(deposit)
        if not release_data:
            continue
        deposit.software_version = release_data.software_version
        deposit.release_notes = release_data.release_notes
        deposit.save()


def cleanup_release_data(apps: Apps, schema_editor: BaseDatabaseSchemaEditor):
    Deposit = apps.get_model("deposit", "Deposit")
    Deposit.objects.filter(
        status=DEPOSIT_STATUS_LOAD_SUCCESS, type=DEPOSIT_CODE
    ).update(software_version="", release_notes="")


class Migration(migrations.Migration):

    dependencies = [
        ("deposit", "0024_deposit_software_version_and_release_notes"),
    ]

    operations = [
        migrations.RunPython(set_release_data, reverse_code=cleanup_release_data)
    ]
