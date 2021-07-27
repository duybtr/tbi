from django.db import models

# Create your models here.
class Transaction(models.Model):
    stmt_date = models.DateField()
    stmt_account_last4 = models.CharField(max_length=4)
    stmt_description = models.CharField(max_length=500)
    stmt_amount = models.DecimalField(max_digits=20, decimal_places=2)
    
    def __str__(self):
        return self.description

class Profile(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=50)
    phone = models.CharField(max_length=150,unique=True)
    profile = models.TextField()
    def __str__(self):
        return self.name