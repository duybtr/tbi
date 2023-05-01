from django.contrib import admin
from .models import Transaction, Property, Expense, Expense_Category, Revenue, Document, Rental_Unit, Raw_Invoice, Statement

# Register your models here.
admin.site.register([Transaction, Expense, Expense_Category, Revenue, Document, Property, Rental_Unit, Raw_Invoice, Statement])