from django import forms

class StatementUploadForm(forms.Form):
    choices = [
        ('credit_card', 'Credit Card'),
        ('bank', 'Bank')
    ]
    statement_type = forms.ChoiceField(choices=choices)
    uploaded_file = forms.FileField()

class TransactionUpdateForm(forms.Form):
    statement_types = [
        ('credit_card', 'Credit Card'),
        ('bank', 'Bank')
    ]
    account_classifications = [
        ('expense', 'Expense'),
        ('revenue', 'Revenue')
    ]

    transaction_date = forms.DateField()
    account_number = forms.CharField()
    statement_type = forms.ChoiceField(choices=statement_types)
    transaction_description = forms.TextField()
    transaction_amount = forms.DecimalField()
    document_image = forms.FileField()
    accounting_classification = forms.ChoiceField(choices=account_classifications)
