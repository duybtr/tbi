# transactions/views.py

from django.views.generic import TemplateView
import csv, io
from django.shortcuts import render
from django.contrib import messages
from .models import Transaction, Expense, Revenue, Statement
from .forms import StatementUploadForm, TransactionUpdateForm, CreateExpenseForm, CreateRevenueForm
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import UpdateView, CreateView, DeleteView
from django.views.generic import ListView
from django.db.models import Q
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
           
           # logging.info("column[6] : {}".format(column[6]))
           # logging.info("transaction_amount_val : {}".format("0" if not column[6] else -1*float(column[6]) ))
            if statement_type == 'credit_card':
                transaction_date_val = convert_date(column[3])
                account_number_val = column[1]
                statement_type_val = 'credit_card'
                transaction_description_val = column[5]
                transaction_amount_val = "0" if not column[6] else -1*float(column[6])               
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
                accounting_classification = '',
            )
        return HttpResponseRedirect(reverse('transaction_list'))

class StatementListView(ListView):
    model = Statement
    context_object_name = 'statements'
    template = 'transactions/statement_list.html'

class StatementDeleteView(ListView):
    model = Statement
    template = 'transactions/statement_delete.html'
    success_url = reverse_lazy('statement_delete')

class TransactionListView(ListView):
    model = Transaction
    context_object_name = 'transactions'
    template = 'transactions/transaction_list.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        start_date = self.request.GET.get('start_date')
        if not start_date:
            start_date = '2008-01-01' 
        end_date = self.request.GET.get('end_date')
        if not end_date:
            end_date = datetime.now()
        if query is None:
            return Transaction.objects.all()
        else:
            return Transaction.objects.filter(
                Q(transaction_description__icontains=query) & Q(transaction_date__range=[start_date, end_date])
            )

class TransactionUpdateView(UpdateView):
    model = Transaction 
    form_class  = TransactionUpdateForm
    template_name = 'transactions/transaction_edit.html'
    success_url = reverse_lazy('transaction_list')

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        transaction = Transaction.objects.get(pk=self.kwargs.get('pk'))
        return render(request, self.template_name, {'form': form, 'transaction': transaction})

class TransactionDeleteView(DeleteView):
    model = Transaction
    template_name = 'transactions/transaction_delete.html'
    success_url = reverse_lazy('transaction_list')

class CreateExpenseView(CreateView):
    model = Expense
    form_class = CreateExpenseForm
    template_name = 'transactions/create_record.html'
    success_url = reverse_lazy('expense_list')

    def get(self, request, *args, **kwargs):
        form =self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            expense_model = form.save(commit=False)
            expense_model.author = request.user
            store_in_gcs(expense_model.document_image, expense_model.GCS_ROOT_BUCKET, expense_model.get_record_folder())
            form.save()
            os.remove(os.path.join(settings.MEDIA_ROOT, expense_model.document_image.name))
            return HttpResponseRedirect(self.success_url)    
        return render(request, self.template_name, {'form': form})

class CreateRevenueView(CreateView):
    model = Revenue
    form_class = CreateRevenueForm
    template_name = 'transactions/create_record.html'
    success_url = reverse_lazy('revenue_list')

    def get(self, request, *args, **kwargs):
        form =self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            revenue_model = form.save(commit=False)
            revenue_model.author = request.user
            store_in_gcs(revenue_model.document_image, revenue_model.GCS_ROOT_BUCKET, revenue_model.get_record_folder())
            form.save()
            os.remove(os.path.join(settings.MEDIA_ROOT, revenue_model.document_image.name))
            return HttpResponseRedirect(self.success_url)    
        return render(request, self.template_name, {'form': form})

class ExpenseListView(ListView):
    model = Expense
    template_name = 'transactions/expense_list.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query is None:
            return Expense.objects.all()
        else:
            return Expense.objects.filter(
                Q(address__address__address__icontains=query) | Q(note__icontains=query) | Q(expense)
            )
            
class RevenueListView(ListView):
    model = Revenue
    template_name = 'transactions/revenue_list.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query is None:
            return Revenue.objects.all()
        else:
            return Revenue.objects.filter(
                Q(address__address__address__icontains=query) | Q(note__icontains=query) | Q(revenue)
            )

class ExpenseUpdateView(UpdateView):
    model = Expense
    form_class = CreateExpenseForm
    template_name = 'transactions/expense_edit.html'
    success_url = reverse_lazy('expense_list')

class RevenueUpdateView(UpdateView):
    model = Revenue
    form_class = CreateRevenueForm
    template_name = 'transactions/revenue_edit.html'
    success_url = reverse_lazy('revenue_list')

class ExpenseDeleteView(DeleteView):
    model = Expense
    template_name = 'transactions/expense_delete.html'
    success_url = reverse_lazy('expense_list')

    def delete(self, *args, **kwargs):
        Transaction.objects.filter(match_id=self.kwargs.get('pk')).update(match_id = 0)
        return super(ExpenseDeleteView, self).delete(*args, **kwargs)

class RevenueDeleteView(DeleteView):
    model = Revenue
    template_name = 'transactions/revenue_delete.html'
    success_url = reverse_lazy('revenue_list')

    def delete(self, *args, **kwargs):
        Transaction.objects.filter(match_id=self.kwargs.get('pk')).update(match_id = 0)
        return super(RevenueDeleteView, self).delete(*args, **kwargs)

class MatchingExpenseListView(ListView):
    model = Expense
    template_name = 'transactions/matching_expense_list.html'

    def get_context_data(self, **kwargs):
        context = super(MatchingExpenseListView, self).get_context_data(**kwargs)
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

class MatchingRevenueListView(ListView):
    model = Revenue
    template_name = 'transactions/matching_revenue_list.html'

    def get_context_data(self, **kwargs):
        context = super(MatchingRevenueListView, self).get_context_data(**kwargs)
        logging.info('kwargs {}'.format(self.kwargs.get('pk')))
        target_transaction = Transaction.objects.get(pk=self.kwargs.get('pk'))
        target_transaction_amount_upper = target_transaction.transaction_amount * Decimal(1.2)
        target_transaction_amount_lower = target_transaction.transaction_amount * Decimal(0.8)
        context['target_transaction'] = target_transaction
        context['object_list'] = Revenue.objects.filter(
            amount__lte=target_transaction_amount_upper
        ).filter(
            amount__gte=target_transaction_amount_lower
        )
        return context
    
def match_expense(request, transaction_pk, expense_pk):
    logging.info("Transaction pk: {} -  Expense pk: {}".format(transaction_pk, expense_pk))
    matching_expense = Expense.objects.get(pk=expense_pk)
    Transaction.objects.filter(pk=transaction_pk).update(match_id=expense_pk)
    return HttpResponseRedirect(reverse('transaction_list'))

def match_revenue(request, transaction_pk, revenue_pk):
    logging.info("Transaction pk: {} -  Revenue pk: {}".format(transaction_pk, revenue_pk))
    matching_revenue = Revenue.objects.get(pk=revenue_pk)
    Transaction.objects.filter(pk=transaction_pk).update(match_id=revenue_pk)
    return HttpResponseRedirect(reverse('transaction_list'))

def remove_match(request, transaction_pk):
    Transaction.objects.filter(pk=transaction_pk).update(match_id=0)
    return HttpResponseRedirect(reverse('transaction_list'))
    