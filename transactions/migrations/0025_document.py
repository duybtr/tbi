# Generated by Django 4.1.4 on 2022-12-18 21:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0024_property_market_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('record_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='transactions.record')),
            ],
            bases=('transactions.record',),
        ),
    ]
