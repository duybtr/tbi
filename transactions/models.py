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

class Profile(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=50)
    phone = models.CharField(max_length=150,unique=True)
    profile = models.TextField()
    def __str__(self):
        return self.name