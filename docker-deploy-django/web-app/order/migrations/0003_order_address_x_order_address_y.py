# Generated by Django 4.2.9 on 2024-04-15 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0002_rename_proudct_order_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='address_x',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='order',
            name='address_y',
            field=models.IntegerField(default=1),
        ),
    ]