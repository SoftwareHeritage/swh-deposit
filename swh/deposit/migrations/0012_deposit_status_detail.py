# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-07-09 13:08
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("deposit", "0011_auto_20180115_1510"),
    ]

    operations = [
        migrations.AddField(
            model_name="deposit",
            name="status_detail",
            field=django.contrib.postgres.fields.jsonb.JSONField(null=True),
        ),
    ]
