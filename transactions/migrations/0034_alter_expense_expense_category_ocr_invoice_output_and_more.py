# Generated by Django 5.0.3 on 2024-04-22 01:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0033_record_document_hash'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='expense_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='transactions.expense_category'),
        ),
        migrations.CreateModel(
            name='OCR_Invoice_Output',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('process_date', models.DateField()),
                ('output_url', models.CharField(max_length=100)),
                ('raw_invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='transactions.raw_invoice')),
            ],
        ),
        migrations.CreateModel(
            name='OCR_Processed_Invoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expense', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='transactions.expense')),
                ('ocr_invoice_output', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='transactions.ocr_invoice_output')),
            ],
        ),
    ]
