# Generated by Django 4.2.9 on 2024-04-23 03:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0005_order_quantity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='ups_account_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]