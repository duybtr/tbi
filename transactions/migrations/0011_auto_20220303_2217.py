# Generated by Django 3.1.12 on 2022-03-04 04:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0010_raw_invoice_tax_year'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='expense_type',
            field=models.CharField(blank=True, choices=[('misc', 'Misc'), ('advertising', 'Advertising'), ('management_fee', 'Management Fee'), ('trash', 'Trash'), ('water', 'Water'), ('power', 'Power'), ('gas', 'Gas'), ('insurance', 'Insurance'), ('repair_maintenance', 'Repair and Maintenance'), ('roof', 'Roof'), ('landscaping', 'Landscaping'), ('commission', 'Commission'), ('taxes_and_fess', 'Taxes & Fees'), ('payroll', 'Payroll'), ('payroll tax', 'Payroll Tax')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='revenue',
            name='revenue_type',
            field=models.CharField(choices=[('reimb', 'Reimbursement'), ('rent', 'Rent'), ('discounts_and_cashbacks', 'Discounts and Cashbacks')], default='rent', max_length=50),
        ),
    ]