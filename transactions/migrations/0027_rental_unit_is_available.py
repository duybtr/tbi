# Generated by Django 4.1.4 on 2023-01-01 20:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0026_alter_record_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='rental_unit',
            name='is_available',
            field=models.BooleanField(default=True),
        ),
    ]
