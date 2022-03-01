from os import path
from django import forms
from .models import Transaction, Expense, Revenue, Statement, Raw_Invoice
from django.forms.widgets import ClearableFileInput
from datetime import datetime

class CustomClearableFileInput(ClearableFileInput):
    def get_context(self, name, value, attrs):
        #value.name = path.basename(value.name)
        context = super().get_context(name, value, attrs)       
        return context

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
       exclude = ['statement', 'transaction_date', 'match_id']

class RawInvoiceUpdateForm(forms.ModelForm):
    class Meta:
        model = Raw_Invoice
        exclude = ['upload_date','invoice_image','date_filed','author']

class CreateExpenseForm(forms.ModelForm):
    #document_image = forms.FileField(widget=CustomClearableFileInput)
    class Meta:
        model = Expense
        exclude = ['author', 'date_uploaded','date_filed','raw_invoice']
        
class CreateRevenueForm(forms.ModelForm):
    class Meta:
        model = Revenue
        exclude = ['author', 'date_uploaded']

class UploadMultipleInvoicesForm(forms.Form):
    current_year = datetime.now().year
    years = [(str(i), str(i)) for i in range(current_year-2, current_year+2)]
    tax_year = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        choices=years,
        initial=str(current_year),
    )
    invoices = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True})) 
    
    
