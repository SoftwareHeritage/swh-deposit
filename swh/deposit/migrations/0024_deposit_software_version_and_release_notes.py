# Copyright (C) 2024 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("deposit", "0023_alter_deposit_status_detail_alter_deposit_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="deposit",
            name="software_version",
            field=models.TextField(default=""),
        ),
        migrations.AddField(
            model_name="deposit",
            name="release_notes",
            field=models.TextField(default=""),
        ),
    ]
