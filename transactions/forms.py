from django import forms
from .models import Transaction, Expense, Revenue, Statement
class StatementUploadForm(forms.ModelForm):
    class Meta:
        model = Statement
        exclude = ['author', 'date_uploaded']
        labels = {
            'uploaded_file': 'Upload a file'
        }

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

class UploadMultipleInvoicesForm(forms.Form):
    invoices = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True})) 
