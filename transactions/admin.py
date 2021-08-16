from django.contrib import admin
from .models import Transaction, Property, Expense, Rental_Unit

# Register your models here.
admin.site.register([Transaction, Expense, Property, Rental_Unit])