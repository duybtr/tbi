from django.db import models
from django.contrib.auth import get_user_model
from common.utils import format_for_storage
from datetime import datetime
from django.conf import settings
from common.utils import store_in_gcs, GCS_ROOT_BUCKET, get_full_path_to_gcs
import os

#logging.basicConfig(filename='example.log', level=logging.DEBUG)

# Create your models here.
class Statement(models.Model):
    record_dir = 'statements'

    choices = [
        ('credit_card', 'Credit Card'),
        ('bank', 'Bank')
    ]

    period_ending_date = models.DateField()
    account_number = models.CharField(max_length=4)
    statement_type = models.CharField(max_length=20, choices=choices)
    uploaded_file = models.FileField()
    is_verified = models.BooleanField()
    author = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE
    ) 
    date_uploaded = models.DateField(auto_now=True)

    def get_full_path_to_gcs(self):
        year = self.period_ending_date.year
        return 'https://storage.cloud.google.com/{}/{}/{}'.format(GCS_ROOT_BUCKET, self.get_statement_folder(), self.uploaded_file.name)
    
    def get_statement_folder(self):
        year = self.period_ending_date.year
        return '{}/{}'.format(self.record_dir, year)
    def save(self, *args, **kwargs):
        ## Looks a bit hacky but this needs to happen in this exact sequence. 
        # If we try to delete the file before saving, then we would get the 'file is being processed error'.
        if self.uploaded_file.name:
            store_in_gcs([self.uploaded_file], GCS_ROOT_BUCKET, self.get_statement_folder())
        super().save(*args, **kwargs)

class Transaction(models.Model):
    transaction_date = models.DateField()
    statement = models.ForeignKey(
        Statement,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_description = models.TextField(max_length=500)
    transaction_amount = models.DecimalField(max_digits=20, decimal_places=2)
    match_id = models.BigIntegerField(default=0)
    is_ignored = models.BooleanField(default=False)
    
    def __str__(self):
        return self.transaction_description
    
    def get_matching_record(self):
        if self.transaction_amount >= 0:
            return Revenue.objects.get(pk=self.match_id)
        else:
            return Expense.objects.get(pk=self.match_id)

    matching_record = property(get_matching_record)

class Property(models.Model):
    address = models.CharField(max_length=50)
    market_price = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    def __str__(self):
        return self.address

class Rental_Unit(models.Model):
    address = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='rental_units'
    )
    suite = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return '{} {}'.format(self.address, self.suite)

class Raw_Invoice(models.Model):
    directory = 'unfiled_invoices'
    upload_date = models.DateField(auto_now=True)
    invoice_image = models.FileField()
    #tax_year = models.IntegerField()
    date_filed = models.DateTimeField(blank=True, null=True)
    need_review = models.BooleanField(default=False)
    note = models.TextField(max_length = 500, default="", blank=True, null=True)
    author = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        blank = True,
        null = True,
    )
    
    def get_full_path_to_gcs(self):
        return get_full_path_to_gcs(self.get_relative_path_to_gcs())

    def get_relative_path_to_gcs(self):
        return '{}/{}'.format(self.directory, self.invoice_image.name)
    
    def __str__(self):
        return self.invoice_image.name


class Record(models.Model):
    GCS_ROOT_BUCKET = 'tran_ba_investment_group_llc'

    record_dir = 'temp'

    record_date = models.DateField()
    address = models.ForeignKey(
        Rental_Unit,
        on_delete=models.CASCADE,
        related_name='records',
    )
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    document_image = models.FileField(blank=True, null=True)
    note = models.TextField(max_length = 500, blank=True, null=True)

    date_filed = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
    )

    def get_full_path_to_gcs(self):
        return get_full_path_to_gcs(self.get_relative_path_to_gcs())

    def get_relative_path_to_gcs(self):
        year = self.record_date.year
        return '{}/{}'.format(self.get_record_folder(), self.document_image.name)
    
    def get_record_folder(self):
        formatted_address = format_for_storage(str(self.address.address))
        year = self.record_date.year
        return '{}/{}/{}'.format(formatted_address, self.record_dir, year)
    
class Expense(Record):
    record_dir = 'invoices'
    EXPENSE_TYPES = (
        ("misc", "Misc"),
        ('advertising', 'Advertising'),
        ('management_fee', 'Management Fee'),
        ('trash', 'Trash'),
        ('water', 'Water'),
        ('power', 'Power'),
        ('insurance', 'Insurance'),
        ('repair_maintenance', 'Repair and Maintenance'),
        ('roof', 'Roof'),
        ('landscaping', 'Landscaping'),
        ('commission', 'Commission'),
        ('taxes_and_fess', 'Taxes & Fees')
    )
    raw_invoice = models.ForeignKey(
        Raw_Invoice,
        models.SET_NULL,
        blank=True,
        null=True,
    )
    expense_type = models.CharField(max_length=50, choices = EXPENSE_TYPES, blank=True, null=True)
        
class Revenue(Record):
    record_dir = 'checks'
    REVENUE_TYPES = (
        ('reimb','Reimbursement'),
        ('rent', 'Rent')
    )
    revenue_type = models.CharField(max_length=50, choices = REVENUE_TYPES, default='rent')

