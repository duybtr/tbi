# Generated by Django 3.1.12 on 2021-09-11 20:19

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0020_auto_20210908_2231'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='is_verified',
        ),
        migrations.AlterField(
            model_name='expense',
            name='date_uploaded',
            field=models.DateTimeField(default=datetime.datetime(2021, 9, 11, 15, 19, 17, 710631)),
        ),
    ]
