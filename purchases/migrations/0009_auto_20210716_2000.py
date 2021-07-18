# Generated by Django 3.2.4 on 2021-07-16 20:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("purchases", "0005_income"),
    ]

    operations = [
        migrations.AddField(
            model_name="income",
            name="amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True
            ),
        ),
        migrations.AddField(
            model_name="purchase",
            name="amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True
            ),
        ),
    ]