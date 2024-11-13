from django.db import migrations, models

from swh.deposit.api.common import guess_deposit_origin_url


def fill_origin_url(apps, schema_editor):
    Deposit = apps.get_model("deposit", "Deposit")
    for deposit in Deposit.objects.all():
        if deposit.origin_url is None:
            deposit.origin_url = guess_deposit_origin_url(deposit)
            deposit.save()


class Migration(migrations.Migration):
    dependencies = [
        ("deposit", "0020_auto_20200929_0855"),
    ]

    operations = [
        migrations.AddField(
            model_name="deposit",
            name="origin_url",
            field=models.TextField(null=True),
        ),
        # migrations.RunPython(fill_origin_url),
        migrations.AlterField(
            model_name="deposit",
            name="external_id",
            field=models.TextField(null=True),
        ),
    ]
