from django.db import models

# Create your models here.
class Transaction(models.Model):
    transaction_date = models.DateField()
    account_number = models.CharField(max_length=4)
    statement_type = models.CharField(max_length=20)
    transaction_description = models.TextField(max_length=500)
    transaction_amount = models.DecimalField(max_digits=20, decimal_places=2)
    document_image = models.FileField()
    is_verified = models.BooleanField()
    accounting_classification = models.CharField(max_length=20)
    
    def __str__(self):
        return self.transaction_description

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
    GCS_ROOT_BUCKET = 'tbi-document-images'

    expense_date = models.DateField()
    address = models.ForeignKey(
        Property,
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

    def display_full_path_to_gcs(self):
        return 'https://storage.cloud.google.com/tbi_document_images/{}'.format(self.invoice_image.name)
