# Generated by Django 3.1.12 on 2021-09-07 21:47

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0018_auto_20210907_1647'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='date_uploaded',
            field=models.DateTimeField(default=datetime.datetime(2021, 9, 7, 16, 47, 33, 661042)),
        ),
    ]
