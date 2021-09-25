from django import forms
from .models import Transaction, Expense, Revenue, Statement
class StatementUploadForm(forms.Form):
    class Meta:
        model = Statement
        exclude = ['author', 'date_uploaded']

class TransactionUpdateForm(forms.ModelForm):
   class Meta:
       model = Transaction
       fields = '__all__'

class CreateExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        exclude = ['author', 'date_uploaded']

class CreateRevenueForm(forms.ModelForm):
    class Meta:
        model = Revenue
        exclude = ['author', 'date_uploaded']