# transactions/views.py

from django.views.generic import TemplateView
import csv, io
from django.shortcuts import render
from django.contrib import messages
from .models import Transaction, Expense
from .forms import StatementUploadForm, TransactionUpdateForm, CreateExpenseForm
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import UpdateView, CreateView
from django.views.generic import ListView
from common.utils import store_in_gcs
from google.cloud import storage
import logging
from datetime import datetime
import os
from decimal import Decimal
from django.conf import settings

logging.basicConfig(filename='example.log', level=logging.DEBUG)

class HomePageView(TemplateView):
    template_name = 'home.html'

class AboutPageView(TemplateView):
    template_name = 'about.html'

def convert_date(dt_string):
    return datetime.strptime(dt_string, '%m/%d/%Y').strftime('%Y-%m-%d')
def convert_decimal(amount):
    if not amount:
        return 0
    return amount

def statement_upload(request):
    
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
                is_verified = False,
                accounting_classification = '',
            )
        return HttpResponseRedirect(reverse('transaction_list'))
def transaction_list(request):
    template = 'transactions/transaction_list.html'
    transactions = Transaction.objects.all()
    matching_expenses = Expense.objects.filter(pk__in = [t.match_id for t in transactions])

    context = {'transactions': transactions }
    return render(request, template, context)



class TransactionUpdateView(UpdateView):
    model = Transaction 
    form_class = TransactionUpdateForm
    template_name = 'transactions/transaction_edit.html'
    success_url = reverse_lazy('transaction_list')

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        store_in_gcs(form.files['document_image'], 'tbi_document_images')
        return super().form_valid(form)

class CreateExpenseView(CreateView):
    model = Expense
    form_class = CreateExpenseForm
    template_name = 'transactions/create_expense.html'
    success_url = reverse_lazy('expense_list')

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            expense_model = form.save(commit=False)
            expense_model.author = request.user
            store_in_gcs(expense_model.invoice_image, expense_model.GCS_ROOT_BUCKET, expense_model.get_expense_folder())
            form.save()
            os.remove(os.path.join(settings.MEDIA_ROOT, expense_model.invoice_image.name))
            return HttpResponseRedirect(self.success_url)    
        return render(request, self.template_name, {'form': form})

class ExpenseListView(ListView):
    model = Expense
    template_name = 'transactions/expense_list.html'

class ExpenseUpdateView(UpdateView):
    model = Expense
    form_class = CreateExpenseForm
    template_name = 'transactions/expense_edit.html'
    success_url = reverse_lazy('expense_list')

class MatchListView(ListView):
    model = Expense
    template_name = 'transactions/match_list.html'

    def get_context_data(self, **kwargs):
        context = super(MatchListView, self).get_context_data(**kwargs)
        logging.info('kwargs {}'.format(self.kwargs.get('pk')))
        target_transaction = Transaction.objects.get(pk=self.kwargs.get('pk'))
        target_transaction_amount_upper = -1*(target_transaction.transaction_amount * Decimal(1.2))
        target_transaction_amount_lower = -1*(target_transaction.transaction_amount * Decimal(0.8))
        context['target_transaction'] = target_transaction
        context['object_list'] = Expense.objects.filter(
            amount__lte=target_transaction_amount_upper
        ).filter(
            amount__gte=target_transaction_amount_lower
        )
        return context
    
def match_expense(request, transaction_pk, expense_pk):
    logging.info("Transaction pk: {} -  Expense pk: {}".format(transaction_pk, expense_pk))
    matching_expense = Expense.objects.get(pk=expense_pk)

    # MyModel.objects.filter(pk=obj.pk).update(val=F('val') + 1)
    # At this point obj.val is still 1, but the value in the database
    # was updated to 2. The object's updated value needs to be reloaded
    # from the database.
    Transaction.objects.filter(pk=transaction_pk).update(match_id=expense_pk)
    return HttpResponseRedirect(reverse('transaction_list'))