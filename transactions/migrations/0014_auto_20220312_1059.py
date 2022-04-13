# Generated by Django 3.1.12 on 2022-03-12 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0013_auto_20220309_1525'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='expense_type',
            field=models.CharField(blank=True, choices=[('misc', 'Misc'), ('advertising', 'Advertising'), ('management_fee', 'Management Fee'), ('trash', 'Trash'), ('water', 'Water'), ('power', 'Power'), ('gas', 'Gas'), ('insurance', 'Insurance'), ('repair_maintenance', 'Repair and Maintenance'), ('roof', 'Roof'), ('landscaping', 'Landscaping'), ('commission', 'Commission'), ('taxes_and_fees', 'Taxes & Fees'), ('payroll', 'Payroll'), ('payroll tax', 'Payroll Tax'), ('property_purchase', 'Property Purchase')], max_length=50, null=True),
        ),
    ]