# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-09-24 10:03
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.auth.models
import django.contrib.postgres.fields
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dbversion',
            fields=[
                ('version', models.IntegerField(primary_key=True, serialize=False)),
                ('release', models.DateTimeField(default=django.utils.timezone.now, null=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'dbversion',
            },
        ),
        migrations.CreateModel(
            name='Deposit',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('reception_date', models.DateTimeField(auto_now_add=True)),
                ('complete_date', models.DateTimeField(null=True)),
                ('external_id', models.TextField()),
                ('swh_id', models.TextField(blank=True, null=True)),
                ('status', models.TextField(choices=[('partial', 'partial'), ('expired', 'expired'), ('ready', 'ready'), ('injecting', 'injecting'), ('success', 'success'), ('failure', 'failure')], default='partial')),
            ],
            options={
                'db_table': 'deposit',
            },
        ),
        migrations.CreateModel(
            name='DepositClient',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('collections', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), null=True, size=None)),
            ],
            options={
                'db_table': 'deposit_client',
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='DepositCollection',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('name', models.TextField()),
            ],
            options={
                'db_table': 'deposit_collection',
            },
        ),
        migrations.CreateModel(
            name='DepositRequest',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('metadata', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                ('deposit', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='deposit.Deposit')),
            ],
            options={
                'db_table': 'deposit_request',
            },
        ),
        migrations.CreateModel(
            name='DepositRequestType',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('name', models.TextField()),
            ],
            options={
                'db_table': 'deposit_request_type',
            },
        ),
        migrations.AddField(
            model_name='depositrequest',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='deposit.DepositRequestType'),
        ),
        migrations.AddField(
            model_name='deposit',
            name='client',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='deposit.DepositClient'),
        ),
        migrations.AddField(
            model_name='deposit',
            name='collection',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='deposit.DepositCollection'),
        ),
    ]