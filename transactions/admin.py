from django.contrib import admin
from .models import Transaction, Property, Expense, Document, Rental_Unit, Raw_Invoice, Statement

# Register your models here.
admin.site.register([Transaction, Expense, Document, Property, Rental_Unit, Raw_Invoice, Statement])