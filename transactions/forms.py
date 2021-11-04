from os import path
from django import forms
from .models import Transaction, Expense, Revenue, Statement
from django.forms.widgets import ClearableFileInput
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
       fields = '__all__'

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
    invoices = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True})) 
