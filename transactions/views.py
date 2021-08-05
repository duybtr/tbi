# transactions/views.py

from django.views.generic import TemplateView
import csv, io
from django.shortcuts import render
from django.contrib import messages
from .models import Transaction
from .forms import StatementUploadForm
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import UpdateView
import logging
import datetime


class HomePageView(TemplateView):
    template_name = 'home.html'

class AboutPageView(TemplateView):
    template_name = 'about.html'

def convert_date(dt_string):
    return datetime.datetime.strptime(dt_string, '%m/%d/%Y').strftime('%Y-%m-%d')
def convert_decimal(amount):
    if not amount:
        return 0
    return amount

def statement_upload(request):
    logging.basicConfig(filename='example.log', level=logging.DEBUG)
    # declaring template
    template = 'transactions/statement_upload.html'
    
    if request.method == "GET":
        form = StatementUploadForm()
        context = {'form':form}
        return render(request, template, context)
    form = StatementUploadForm(request.POST, request.FILES)
    if form.is_valid():
        logging.info(form.cleaned_data['statement_type'])
        logging.info(form.cleaned_data['uploaded_file'])
        csv_file = form.cleaned_data['uploaded_file']
        statement_type = form.cleaned_data['statement_type']
        if statement_type == 'credit_card':
            logging.info('The user just uploaded a credit_card statement')
        elif statement_type == 'bank':
            logging.info('The user just uploaded a bank statement')
        # let's check if it is a csv file
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'THIS IS NOT A CSV FILE')
        data_set = csv_file.read().decode('UTF-8')
        # setup a stream which is when we loop through each line we are able to handle a data in a stream
        io_string = io.StringIO(data_set)
        next(io_string)
        for column in csv.reader(io_string, delimiter='|', quotechar='"'):
            column_map = {}
            if statement_type == 'credit_card':
                transaction_date_val = convert_date(column[3])
                account_number_val = column[1]
                statement_type_val = 'credit_card'
                transaction_description_val = column[5]
                transaction_amount_val = column[6]
            elif statement_type == 'bank':
                transaction_date_val = convert_date(column[0])
                account_number_val = '1538'
                statement_type_val = 'bank'
                transaction_description_val = column[1]
                transaction_amount_val = "0" if not column[2] else column[2]
            _, created = Transaction.objects.update_or_create(
                transaction_date = transaction_date_val,
                account_number = account_number_val,
                statement_type = statement_type_val,
                transaction_description = transaction_description_val,
                transaction_amount = transaction_amount_val,
                document_image = '',
                is_verified = False,
                accounting_classification = '',
            )
        return HttpResponseRedirect(reverse('transaction_list'))
def transaction_list(request):
    template = 'transactions/transaction_list.html'
    data = Transaction.objects.all()
    context = {'transactions': data }
    return render(request, template, context)

class TransactionUpdateView(UpdateView):
    model = Transaction 
    form_class = TransactionUpdateForm
    fields = '__all__'
    template_name = 'transactions/transaction_edit.html'
    success_url = reverse_lazy('transaction_list')

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        form.send_email()
        return super().form_valid(form)