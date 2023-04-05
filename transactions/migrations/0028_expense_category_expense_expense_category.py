# Generated by Django 4.1.4 on 2023-04-04 23:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0027_rental_unit_is_available'),
    ]

    operations = [
        migrations.CreateModel(
            name='Expense_Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expense_category', models.CharField(max_length=50)),
            ],
        ),
        migrations.AddField(
            model_name='expense',
            name='expense_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='expense_categories', to='transactions.expense_category'),
        ),
    ]
