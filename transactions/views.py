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
import os, sys
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

class StatementCreateView(CreateView):
    model = Statement
    form_class = StatementUploadForm
    template_name = 'transactions/statement_upload.html'
    success_url = reverse_lazy('statement_list')

    def get(self, request, *args, **kwargs):
        form =self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            statement_model = form.save(commit=False)
            csv_file = form.cleaned_data['uploaded_file']
            if not csv_file.name.endswith('.csv') or not csv_file.name.endswith('.dat'):
                messages.error(request, 'THIS IS NOT A CSV FILE')
            statement_model.author = request.user
            store_in_gcs(statement_model.uploaded_file, statement_model.GCS_ROOT_BUCKET, statement_model.get_statement_folder())
            statement_model = form.save()
            populate_transaction_table(csv_file, statement_model)
            os.remove(os.path.join(settings.MEDIA_ROOT, statement_model.uploaded_file.name))
            return HttpResponseRedirect(self.success_url)   

        return render(request, self.template_name, {'form': form})

def populate_transaction_table(csv_file, statement_model):
    logging.info("file : {}".format(csv_file.name))
    statement_type = statement_model.statement_type
    statement_id = statement_model.id
    with(open(csv_file.name, newline='')) as csv_file:
        reader = csv.reader(csv_file, delimiter='|', quotechar='"')
        for index,row in enumerate(reader):
            # skipping summary rows and header rows
            skip_range = range(0,8) if statement_type == 'bank' else range(0,5)
            if index in skip_range:
                continue
            else:
                if statement_type == 'credit_card':
                    transaction_date_val = convert_date(row[3])
                    transaction_description_val = row[5]
                    transaction_amount_val = "0" if not row[6] else -1*float(row[6])               
                elif statement_type == 'bank':
                    transaction_date_val = convert_date(row[0])
                    transaction_description_val = row[1]
                    transaction_amount_val = "0" if not row[2] else row[2]
                _, created = Transaction.objects.update_or_create(
                    transaction_date = transaction_date_val,
                    statement_id = statement_id,
                    transaction_description = transaction_description_val,
                    transaction_amount = transaction_amount_val
                )

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
        q = Q()
        query = self.request.GET.get('q')
        statement_id = self.request.GET.get('statement_id')
        start_date = self.request.GET.get('start_date')
        if not start_date:
            start_date = '2008-01-01' 
        end_date = self.request.GET.get('end_date')
        if not end_date:
            end_date = datetime.now()
        q = Q(transaction_date__range=[start_date, end_date])
        if not query is None:
            q = q & Q(transaction_description__icontains=query)
        if not statement_id is None:
            q = q & Q(statement_id__exact=statement_id)
        return Transaction.objects.filter(q);

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

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            expense_model = form.save(commit=False)
            expense_model.author = request.user
            form.save()   
            return HttpResponseRedirect(self.success_url)    
        return render(request, self.template_name, {'form': form})

class CreateRevenueView(CreateView):
    model = Revenue
    form_class = CreateRevenueForm
    template_name = 'transactions/create_record.html'
    success_url = reverse_lazy('revenue_list')

    def get(self, request, *args, **kwargs):
        target_transaction = None
        pk = self.kwargs.get('pk')
        context = {}
        form = self.form_class(initial=self.initial)
        if pk:
            target_transaction = Transaction.objects.get(pk=pk)
            if not target_transaction is None:
                context['target_transaction'] = target_transaction
                form =self.form_class(initial={
                    'record_date':target_transaction.transaction_date, 
                    'amount':target_transaction.transaction_amount, 
                    'note':target_transaction.transaction_description
                })               
        context['form'] = form
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            revenue_model = form.save(commit=False)
            revenue_model.author = request.user
            form.save()
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
    