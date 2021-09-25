# Generated by Django 3.1.12 on 2021-09-25 04:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('transactions', '0004_auto_20210918_2330'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='account_number',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='accounting_classification',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='statement_type',
        ),
        migrations.CreateModel(
            name='Statement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_ending_date', models.DateField()),
                ('account_number', models.CharField(max_length=4)),
                ('statement_type', models.CharField(max_length=20)),
                ('statement_file', models.FileField(upload_to='')),
                ('upload_date', models.DateField()),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='transaction',
            name='statement',
            field=models.ForeignKey(default='10/23/1988', on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='transactions.statement'),
            preserve_default=False,
        ),
    ]
