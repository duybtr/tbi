# Generated by Django 3.1.12 on 2022-01-04 04:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0003_merge_20220103_2226'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='raw_invoice',
            name='need_review',
        ),
        migrations.RemoveField(
            model_name='raw_invoice',
            name='note',
        ),
    ]