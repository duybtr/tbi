# Generated by Django 4.1.4 on 2023-06-28 15:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0028_expense_category_expense_expense_category'),
    ]

    operations = [
        migrations.RenameField(
            model_name='rental_unit',
            old_name='is_available',
            new_name='is_current',
        ),
        migrations.RemoveField(
            model_name='expense',
            name='expense_type',
        ),
    ]
