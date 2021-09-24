from django import forms
from .models import Transaction, Expense, Revenue
class StatementUploadForm(forms.Form):
    choices = [
        ('credit_card', 'Credit Card'),
        ('bank', 'Bank')
    ]
    statement_type = forms.ChoiceField(choices=choices)
    uploaded_file = forms.FileField()

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