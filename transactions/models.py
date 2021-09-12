from django.db import models
from django.contrib.auth import get_user_model
from common.utils import format_for_storage
from datetime import datetime

# Create your models here.
class Transaction(models.Model):
    transaction_date = models.DateField()
    account_number = models.CharField(max_length=4)
    statement_type = models.CharField(max_length=20)
    transaction_description = models.TextField(max_length=500)
    transaction_amount = models.DecimalField(max_digits=20, decimal_places=2)
    #is_verified = models.BooleanField()
    match_id = models.BigIntegerField()
    ACCOUNTING_CLASSIFICATIONS = (
        ("revenue", "Revenue"),
        ("expense", "Expense") 
    )
    accounting_classification = models.CharField(max_length=20, choices=ACCOUNTING_CLASSIFICATIONS, blank=True)
    
    def __str__(self):
        return self.transaction_description
    
    def get_matching_expense(self):
        return Expense.objects.get(pk=self.match_id)

    matching_expense = property(get_matching_expense)

class Property(models.Model):
    address = models.CharField(max_length=50)
    market_price = models.DecimalField(max_digits=20, decimal_places=2)

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

class Expense(models.Model):
    GCS_ROOT_BUCKET = 'tran_ba_investment_group_llc'

    expense_date = models.DateField()
    address = models.ForeignKey(
        Rental_Unit,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    EXPENSE_TYPES = (
        ("misc", "Misc"),
        ('advertising', 'Advertising'),
        ('management_fee', 'Management Fee'),
        ('trash', 'Trash'),
        ('water', 'Water'),
        ('power', 'Power'),
        ('repair_maintenance', 'Repair and Maintenance'),
        ('roof', 'Roof'),
        ('landscaping', 'Landscaping'),
        ('commission', 'Commission')
    )
    expense_type = models.CharField(max_length=50, choices = EXPENSE_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)

    invoice_image = models.FileField()
    note = models.TextField(max_length = 500)

    date_uploaded = models.DateTimeField(default=datetime.now())
    author = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE
    )

    def display_full_path_to_gcs(self):
        year = self.expense_date.year
        return 'https://storage.cloud.google.com/{}/{}/{}'.format(self.GCS_ROOT_BUCKET, self.get_expense_folder(), self.invoice_image.name)
    
    def get_expense_folder(self):
        formatted_address = format_for_storage(str(self.address.address))
        year = self.expense_date.year
        return '{}/{}/{}'.format(formatted_address, 'invoices', year)
    
    


