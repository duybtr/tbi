# Generated by Django 3.1.12 on 2022-04-04 00:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0017_raw_invoice_file_hash'),
    ]

    operations = [
        migrations.AlterField(
            model_name='raw_invoice',
            name='file_hash',
            field=models.TextField(max_length=32, unique=True),
        ),
    ]
