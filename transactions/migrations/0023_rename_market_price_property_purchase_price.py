# Generated by Django 4.0.4 on 2022-08-26 15:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0022_property_full_address'),
    ]

    operations = [
        migrations.RenameField(
            model_name='property',
            old_name='market_price',
            new_name='purchase_price',
        ),
    ]