from os import path
from django import forms
from .models import Transaction, Expense, Revenue, Statement, Raw_Invoice, Rental_Unit, Document
from django.forms.widgets import ClearableFileInput
from datetime import datetime

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
       exclude = ['statement', 'transaction_date', 'match_id','transaction_amount']

class RawInvoiceUpdateForm(forms.ModelForm):
    class Meta:
        model = Raw_Invoice
        exclude = ['upload_date', 'file_hash', 'invoice_image','date_filed','author']

class CreateExpenseForm(forms.ModelForm):
    address = forms.ModelChoiceField(queryset=Rental_Unit.objects.filter(is_current=True).order_by('address__address','suite'))
    class Meta:
        model = Expense
        exclude = ['author', 'date_uploaded','date_filed','raw_invoice','next','document_hash']
        #widgets = {'next' :  forms.HiddenInput()}

class UpdateRevenueForm(forms.ModelForm):
    class Meta:
        model = Revenue
        exclude = ['author', 'date_uploaded', 'document_hash']

class UpdateExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        exclude = ['author', 'date_uploaded', 'date_filed','raw_invoice', 'document_hash']

class CreateRevenueForm(forms.ModelForm):
    address = forms.ModelChoiceField(queryset=Rental_Unit.objects.filter(is_current=True).order_by('address__address','suite'))
    class Meta:
        model = Revenue
        exclude = ['date_uploaded', 'author', 'document_hash']
        #widgets = {'author' :  forms.HiddenInput()}

# class UpdateTransactionForm(forms.ModelForm):
#     class Meta:
#         model = Transaction
#         fields = ['transaction_description']

class UploadDocumentForm(forms.ModelForm):
    address = forms.ModelChoiceField(queryset=Rental_Unit.objects.order_by('address__address','suite'))
    class Meta:
        model = Document
        exclude = ['author', 'date_uploaded', 'amount', 'document_hash']

class SelectTaxYearForm(forms.Form):
    current_year = datetime.now().year
    start_year = 2021
    end_year = current_year
    years = [(str(i), str(i)) for i in range(start_year, current_year+1)]
    tax_year = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        choices=years,
        initial=str(current_year),
    )

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class UploadMultipleInvoicesForm(forms.Form):
    current_year = datetime.now().year
    years = [(str(i), str(i)) for i in range(current_year-2, current_year+2)]
    tax_year = forms.ChoiceField(
        required=False,
        widget=forms.Select,
        choices=years,
        initial=str(current_year),
    )
    invoices = MultipleFileField()


