from django import forms

class StatementUploadForm(forms.Form):
    choices = [
        ('credit_card', 'Credit Card'),
        ('bank', 'Bank')
    ]
    statement_type = forms.ChoiceField(choices=choices)
    uploaded_file = forms.FileField()
