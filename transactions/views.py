# transactions/views.py

from django.views.generic import TemplateView
import csv, io
from django.shortcuts import render
from django.contrib import messages
from .models import Transaction, Expense, Revenue, Statement, Raw_Invoice
from .forms import StatementUploadForm, TransactionUpdateForm, CreateExpenseForm, CreateRevenueForm, UploadMultipleInvoicesForm, RawInvoiceUpdateForm
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import UpdateView, CreateView, DeleteView, FormView
from django.views.generic import ListView
from django.db.models import Q, Value, TextField
from django.db.models.functions import Concat
from common.utils import store_files, format_for_storage, list_blobs, get_full_path_to_gcs, rename_blob, store_in_gcs, GCS_ROOT_BUCKET, delete_file, get_paginator_object
from google.cloud import storage
from django.core.paginator import Paginator
import logging
import google.cloud.logging
from datetime import datetime
import os, sys
from decimal import Decimal
from django.conf import settings
from hashlib import md5
from django.core.files.storage import default_storage
import pdb

# Initialize logging
# Instantiates a client
client = google.cloud.logging.Client()

# Retrieves a Cloud Logging handler based on the environment
# you're running in and integrates the handler with the
# Python logging module. By default this captures all logs
# at INFO level and higher
client.setup_logging()

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
            statement_model = form.save()
            populate_transaction_table(csv_file, statement_model)
            if csv_file.name:
                os.remove(os.path.join(settings.MEDIA_ROOT, csv_file.name))
            return HttpResponseRedirect(self.success_url)   

        return render(request, self.template_name, {'form': form})

def populate_transaction_table(csv_file, statement_model):
    #logging.info("file : {}".format(csv_file.name))
    statement_type = statement_model.statement_type
    statement_id = statement_model.id
    full_file_path = settings.MEDIA_ROOT + '/' + csv_file.name
    with(open(full_file_path, newline='')) as csv_file:
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
    ordering = ['statement_type', 'account_number', 'period_ending_date']

class StatementDeleteView(DeleteView):
    model = Statement
    # not sure why this doesn't work
    # template = 'transactions/statement_delete.html' 
    context_object_name = 'statement'
    success_url = reverse_lazy('statement_list')
        
    def delete(self, *args, **kwargs):
        statement = Statement.objects.get(pk=self.kwargs.get('pk'))
        if statement.uploaded_file.name:
            delete_file(statement.uploaded_file, statement.get_statement_folder())
        return super(StatementDeleteView, self).delete(*args, **kwargs)
class TransactionListView(ListView):
    model = Transaction
    context_object_name = 'transactions'
    template_name = 'transactions/transaction_list.html'

    def add_filters(self):
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
            try:
                target_amount = float(query)
                lower,upper = sorted((0.9*target_amount, 1.1*target_amount))
                q = q & Q(transaction_amount__gte=lower) & Q(transaction_amount__lte=upper)
                q = q | Q(transaction_description__icontains=query)
            except ValueError:
                q = q & Q(transaction_description__icontains=query)
        return q

    def get_queryset(self):
        q = self.add_filters()
        return Transaction.objects.filter(q).order_by('statement__statement_type', 'statement__account_number', 'transaction_date')
    
    def get(self, request, *args, **kwargs):
        results = self.get_queryset()
        page_obj = get_paginator_object(results, 50, request)
        return render(request, self.template_name, {'page_obj': page_obj})

class UnmatchedTransactionListView(TransactionListView):
    model = Transaction
    context_object_name = 'transactions'
    template_name = 'transactions/transaction_list.html'
    def add_filters(self):
        q = super().add_filters()
        q = q & Q(match_id=0) & Q(is_ignored=False)
        return q

class TransactionUpdateView(UpdateView):
    model = Transaction 
    form_class  = TransactionUpdateForm
    template_name = 'transactions/transaction_edit.html'
    success_url = reverse_lazy('transaction_list')

    def get(self, request, *args, **kwargs):
        transaction = Transaction.objects.get(pk=self.kwargs.get('pk'))
        form = self.form_class(initial={
            'transaction_amount':transaction.transaction_amount,
            'transaction_description':transaction.transaction_description,
            'transaction_date':transaction.transaction_date,
            'statement_type':transaction.statement.statement_type,
            'is_ignored': transaction.is_ignored
        })
        return render(request, self.template_name, {'form': form, 'transaction': transaction})
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        transaction = Transaction.objects.get(pk=self.kwargs.get('pk'))
        if form.is_valid():
            updated_transaction = form.save(commit=False)
            transaction.is_ignored = updated_transaction.is_ignored
            transaction.transaction_description = updated_transaction.transaction_description
            transaction.save()
            return HttpResponseRedirect(self.success_url)    
        return render(request, self.template_name, {'form': form})
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
            if expense_model.document_image.name:
                store_in_gcs([expense_model.document_image], GCS_ROOT_BUCKET, expense_model.get_record_folder())
            form.save()  
            if expense_model.document_image.name:
                os.remove(os.path.join(settings.MEDIA_ROOT, expense_model.document_image.name))
            return HttpResponseRedirect(self.success_url)    
        return render(request, self.template_name, {'form': form})

class CreateRevenueView(CreateView):
    model = Revenue
    form_class = CreateRevenueForm
    template_name = 'transactions/create_record.html'
    success_url = reverse_lazy('revenue_list')

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            revenue_model = form.save(commit=False)
            revenue_model.author = request.user
            if revenue_model.document_image.name:
                store_in_gcs([revenue_model.document_image], GCS_ROOT_BUCKET, revenue_model.get_record_folder())
            form.save()
            if revenue_model.document_image.name:
                os.remove(os.path.join(settings.MEDIA_ROOT, revenue_model.document_image.name))
            return HttpResponseRedirect(self.success_url)    
        return render(request, self.template_name, {'form': form})

class CreateMatchingRevenueView(CreateView):
    model = Revenue
    form_class = CreateRevenueForm
    template_name = 'transactions/create_record.html'
    success_url = reverse_lazy('unmatched_transaction_list')

    def get(self, request, *args, **kwargs):
        context = {}
        target_transaction = Transaction.objects.get(pk=self.kwargs.get('pk'))
        context['target_transaction'] = target_transaction
        form = self.form_class(initial={
            'record_date':target_transaction.transaction_date, 
            'amount':target_transaction.transaction_amount, 
            'note':target_transaction.transaction_description
        })               
        context['form'] = form
        return render(request, self.template_name, context)
    
    def form_valid(self, form):
        revenue_model = form.save(commit=False)
        revenue_model.author = self.request.user
        form.save()
        Transaction.objects.filter(pk=self.kwargs.get('pk')).update(match_id=revenue_model.pk)
        return super().form_valid(form)

class CreateMatchingExpenseView(CreateView):
    model = Expense
    form_class = CreateExpenseForm
    template_name = 'transactions/create_record.html'
    success_url = reverse_lazy('unmatched_transaction_list')

    def get(self, request, *args, **kwargs):
        context = {}
        target_transaction = Transaction.objects.get(pk=self.kwargs.get('pk'))
        context['target_transaction'] = target_transaction
        form = self.form_class(initial={
            'record_date':target_transaction.transaction_date, 
            'amount':-1*target_transaction.transaction_amount, 
            'note':target_transaction.transaction_description
        })               
        context['form'] = form
        return render(request, self.template_name, context)
    
    def form_valid(self, form):
        expense_model = form.save(commit=False)
        expense_model.author = self.request.user
        form.save()
        Transaction.objects.filter(pk=self.kwargs.get('pk')).update(match_id=expense_model.pk)
        return super().form_valid(form)

class ExpenseListView(ListView):
    model = Expense
    template_name = 'transactions/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 50

    def get_q(self):
        q = Q()
        query = self.request.GET.get('q')
        order_by = self.request.GET.get('order_by')
        current_year = self.request.GET.get('year')
        unmatched_invoice = self.request.GET.get('unmatched_invoice')
        if not query is None:
            for word in query.split(" "):
                if word.isdigit():
                    word = word.strip()
                    target_amount = float(word)
                    lower,upper = sorted((0.95*target_amount, 1.05*target_amount))
                    q = q & Q(amount__gte=lower) & Q(amount__lte=upper)
                    break
                q = q & Q(searchable_text__icontains=word)
        if order_by is None:
            order_by = '-date_filed'
        if current_year != 'all':
            q = q & Q(record_date__year__gte = datetime.now().year)
        return q
    def get_queryset(self):
        query = self.request.GET.get('q')
        queryset = Expense.objects.all()
        if not query is None:
            queryset = queryset.annotate(searchable_text=Concat('address__address__address', Value(' '), 'address__suite', Value(' '), 'expense_type', Value(' '), 'note', output_field=TextField()))
        return queryset.filter(self.get_q()).order_by('-record_date','address__address__address')
    def get(self, request, *args, **kwargs):
        results = self.get_queryset()
        page_obj = get_paginator_object(results, 50, request)
        return render(request, self.template_name, {'page_obj': page_obj})
class UnmatchedExpenseListView(ExpenseListView):
    def get_q(self):
        q = super().get_q()
        all_transactions = Transaction.objects.all()
        match_ids = [transaction.match_id for transaction in list(all_transactions)]
        q = q & ~Q(pk__in = match_ids)
        return q


class RevenueListView(ListView):
    model = Revenue
    template_name = 'transactions/revenue_list.html'
    context_object_name = 'revenues'
    paginate_by = 50

    def get_queryset(self):
        q = Q()
        query = self.request.GET.get('q')
        order_by = self.request.GET.get('order_by')
        current_year = self.request.GET.get('year')
        queryset = Revenue.objects.all()
        queryset = queryset.annotate(address_and_suite=Concat('address__address__address', Value(' '), 'address__suite', output_field=TextField()))
        if not query is None:
            try:
                query = query.strip()
                target_amount = float(query)
                lower,upper = sorted((0.95*target_amount, 1.05*target_amount))
                q = q & Q(amount__gte=lower) & Q(amount__lte=upper)
                q = q | Q(address_and_suite__icontains=query) | Q(note__icontains=query)
            except ValueError:
                q = Q(address_and_suite__icontains=query) | Q(note__icontains=query)
        if current_year != 'all':
            q = q & Q(record_date__year__gte = datetime.now().year) 
        if order_by is None:
            order_by = '-record_date'

        order_by_dict = {'-record_date' :['-record_date', 'address_and_suite'],
                         'new': ['-date_filed', 'address_and_suite'],
                         'address' : ['address_and_suite', '-date_filed']
                        }
        
        return queryset.filter(q).order_by(*order_by_dict[order_by])
    
    def get(self, request, *args, **kwargs):
        results = self.get_queryset()
        page_obj = get_paginator_object(results, 50, request)
        return render(request, self.template_name, {'page_obj': page_obj})

class ExpenseUpdateView(UpdateView):
    model = Expense
    form_class = CreateExpenseForm
    template_name = 'transactions/expense_edit.html'
    success_url = reverse_lazy('expense_list')
    
    def form_valid(self, form):
        
        # grab previous expense from the database
        # Expense.objects.get(pk=pk)
        previous_expense = Expense.objects.get(pk=self.kwargs.get('pk'))
        updated_expense = form.save(commit=False)
        logging.info('Updating expense: Changed_data {}'.format(previous_expense.pk, form.changed_data))
        if 'document_image' in form.changed_data:
            logging.info('Document image was changed')
            logging.info('Previous document was {}'.format(previous_expense.document_image.name))
            if updated_expense.document_image.name:
                logging.info('Updating document to {}'.format(updated_expense.document_image.name))
                store_in_gcs([updated_expense.document_image], GCS_ROOT_BUCKET, updated_expense.get_record_folder())
                form.save()
                os.remove(os.path.join(settings.MEDIA_ROOT, updated_expense.document_image.name))
            else:
                logging.info('Document {} was cleared'.format(previous_expense.document_image.name))
            if previous_expense.document_image.name:       
                delete_file(previous_expense.document_image, previous_expense.get_record_folder())
        return super().form_valid(form)

class RevenueUpdateView(UpdateView):
    model = Revenue
    form_class = CreateRevenueForm
    template_name = 'transactions/revenue_edit.html'
    success_url = reverse_lazy('revenue_list')
    def form_valid(self, form):
        # grab previous revenue from the database
        # Revenue.objects.get(pk=pk)
        previous_revenue = Revenue.objects.get(pk=self.kwargs.get('pk'))
        updated_revenue = form.save(commit=False)
        logging.info('Updating revenue {}: Changed_data {}'.format(previous_revenue.pk, form.changed_data))
        if 'document_image' in form.changed_data:
            logging.info('Document image was changed')
            logging.info('Previous document was {}'.format(previous_revenue.document_image.name))
            if updated_revenue.document_image.name:
                logging.info('Updating document to {}'.format(updated_revenue.document_image.name))
                store_in_gcs([updated_revenue.document_image], GCS_ROOT_BUCKET, updated_revenue.get_record_folder())
                form.save()
                os.remove(os.path.join(settings.MEDIA_ROOT, updated_revenue.document_image.name))
            else:
                logging.info('Document {} was cleared'.format(previous_revenue.document_image.name))
            if previous_revenue.document_image.name:       
                delete_file(previous_revenue.document_image, previous_revenue.get_record_folder())
        return super().form_valid(form)

class ExpenseDeleteView(DeleteView):
    model = Expense
    template_name = 'transactions/expense_delete.html'
    success_url = reverse_lazy('expense_list')

    def delete(self, *args, **kwargs):
        expense = Expense.objects.get(pk=self.kwargs.get('pk'))
        if expense.document_image.name:
            delete_file(expense.document_image, expense.get_record_folder())
        Transaction.objects.filter(match_id=self.kwargs.get('pk')).update(match_id = 0)
        return super(ExpenseDeleteView, self).delete(*args, **kwargs)

class RevenueDeleteView(DeleteView):
    model = Revenue
    template_name = 'transactions/revenue_delete.html'
    success_url = reverse_lazy('revenue_list')

    def delete(self, *args, **kwargs):
        revenue = Revenue.objects.get(pk=self.kwargs.get('pk'))
        if revenue.document_image.name:
            delete_file(revenue.document_image, revenue.get_record_folder())
        Transaction.objects.filter(match_id=self.kwargs.get('pk')).update(match_id = 0)
        return super(RevenueDeleteView, self).delete(*args, **kwargs)

class MatchingExpenseListView(ListView):
    model = Expense
    template_name = 'transactions/matching_expense_list.html'

    def get_context_data(self, **kwargs):
        context = super(MatchingExpenseListView, self).get_context_data(**kwargs)
        #logging.info('kwargs {}'.format(self.kwargs.get('pk')))
        target_transaction = Transaction.objects.get(pk=self.kwargs.get('pk'))
        matched_expenses = Transaction.objects.filter(transaction_amount__lt = 0).values_list('match_id', flat=True)
        target_transaction_amount_upper = -1*(target_transaction.transaction_amount * Decimal(1.1))
        target_transaction_amount_lower = -1*(target_transaction.transaction_amount * Decimal(0.9))
        context['target_transaction'] = target_transaction
        context['object_list'] = Expense.objects.filter(
            amount__lte=target_transaction_amount_upper
        ).filter(
            amount__gte=target_transaction_amount_lower
        ).exclude(
            id__in=matched_expenses
        ).order_by(
            '-amount'
        )
        return context

class MatchingRevenueListView(ListView):
    model = Revenue
    template_name = 'transactions/matching_revenue_list.html'

    def get_context_data(self, **kwargs):
        context = super(MatchingRevenueListView, self).get_context_data(**kwargs)
        #logging.info('kwargs {}'.format(self.kwargs.get('pk')))
        target_transaction = Transaction.objects.get(pk=self.kwargs.get('pk'))
        matched_revenues = Transaction.objects.filter(transaction_amount__gte = 0).values_list('match_id', flat=True)
        target_transaction_amount_upper = target_transaction.transaction_amount * Decimal(1.1)
        target_transaction_amount_lower = target_transaction.transaction_amount * Decimal(0.9)
        context['target_transaction'] = target_transaction
        context['object_list'] = Revenue.objects.filter(
            amount__lte=target_transaction_amount_upper
        ).filter(
            amount__gte=target_transaction_amount_lower
        ).exclude(
            id__in=matched_revenues
        ).order_by(
            '-amount'
        )
        return context
    
def match_expense(request, transaction_pk, expense_pk):
    #logging.info("Transaction pk: {} -  Expense pk: {}".format(transaction_pk, expense_pk))
    matching_expense = Expense.objects.get(pk=expense_pk)
    #target_transaction = Transactions.objects.get(pk=transaction_pk)
    Transaction.objects.filter(pk=transaction_pk).update(match_id=expense_pk)
    #Expense.objects.filter(pk=expense_pk).update(amount=-1*target_transaction.transaction_amount)
    return HttpResponseRedirect(reverse('unmatched_transaction_list'))

def match_revenue(request, transaction_pk, revenue_pk):
    #logging.info("Transaction pk: {} -  Revenue pk: {}".format(transaction_pk, revenue_pk))
    matching_revenue = Revenue.objects.get(pk=revenue_pk)
    Transaction.objects.filter(pk=transaction_pk).update(match_id=revenue_pk)
    return HttpResponseRedirect(reverse('unmatched_transaction_list'))

def remove_match(request, transaction_pk):
    Transaction.objects.filter(pk=transaction_pk).update(match_id=0)
    return HttpResponseRedirect(reverse('transaction_list'))

class UploadMultipleInvoicesView(FormView):
    form_class = UploadMultipleInvoicesForm
    template_name = 'transactions/upload_multiple_invoices.html'
    success_url = reverse_lazy('upload_multiple_invoices')

    def post(self, request, *args, **kwargs):
        directory = 'unfiled_invoices'
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('invoices')
        if form.is_valid():
            tax_year = form.cleaned_data['tax_year']
            for f in files:
                tmp_file_name = format_for_storage(f.name)
                default_storage.save(tmp_file_name, f)
                full_file_path = settings.MEDIA_ROOT + '/' + tmp_file_name
                with open(full_file_path, "rb") as current_file:
                    md5_hash = md5()
                    while True:
                        buf = current_file.read(2**20)
                        if not buf:
                            break
                        md5_hash.update(buf)
                    invoice = Raw_Invoice.objects.create(
                        upload_date = datetime.now(),
                        invoice_image = tmp_file_name,
                        author = request.user,
                        tax_year = int(tax_year),
                        file_hash = md5_hash.hexdigest()
                    )
                    current_file.seek(0)
                    store_in_gcs([current_file], GCS_ROOT_BUCKET, directory)
                invoice.save()
                os.remove(full_file_path)

            return HttpResponseRedirect(self.success_url)
        else:
            return render(request, self.template_name, {'form': form})

class RawInvoiceListView(ListView):
    model = Raw_Invoice
    template_name = 'transactions/raw_invoice_list.html'
    success_url = reverse_lazy('raw_invoices')
    paginate_by = 50

    def get_queryset(self):
        return Raw_Invoice.objects.filter(Q(date_filed__isnull=True) & Q(need_review=False))

class ReviewInvoiceListView(ListView):
    model = Raw_Invoice
    template_name = 'transactions/raw_invoice_list.html'
    success_url = reverse_lazy('raw_invoices')
    paginate_by = 50

    def get_queryset(self):
        return Raw_Invoice.objects.filter(Q(date_filed__isnull=True) & Q(need_review=True))

class ReviewInvoiceEditView(UpdateView):
    model = Raw_Invoice
    form_class = RawInvoiceUpdateForm
    template_name = 'transactions/raw_invoice_edit.html'
    success_url = reverse_lazy('review_invoices')

class RawInvoiceEditView(UpdateView):
    model = Raw_Invoice
    form_class = RawInvoiceUpdateForm
    template_name = 'transactions/raw_invoice_edit.html'
    success_url = reverse_lazy('raw_invoices')

class RawInvoiceDeleteView(DeleteView):
    model = Raw_Invoice
    template_name = 'transactions/raw_invoice_delete.html'
    success_url = reverse_lazy('raw_invoices')

    def delete(self, *args, **kwargs):
        raw_invoice = Raw_Invoice.objects.get(pk=self.kwargs.get('pk'))
        if raw_invoice.invoice_image:
            delete_file(raw_invoice.invoice_image, Raw_Invoice.directory)
        return super(RawInvoiceDeleteView, self).delete(*args, **kwargs)

class FileInvoiceView(UpdateView):
    model = Expense
    form_class = CreateExpenseForm
    success_url = reverse_lazy('raw_invoices')
    template_name = 'transactions/file_invoice.html'

    def get(self, request, *args, **kwargs):
        raw_invoice = None
        pk = self.kwargs.get('pk')
        context = {}
        form = self.form_class(initial=self.initial)
        if pk:
            raw_invoice = Raw_Invoice.objects.get(pk=pk)
            if not raw_invoice is None:
                context['raw_invoice'] = raw_invoice
                form =self.form_class(initial={
                    'document_image': raw_invoice.invoice_image
                })               
        context['form'] = form
        context['raw_invoice'] =  raw_invoice
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            pk = self.kwargs.get('pk')
            expense_model = form.save(commit=False)
            raw_invoice = Raw_Invoice.objects.get(pk=pk)
            expense_model.raw_invoice = raw_invoice
            expense_model.document_image = raw_invoice.invoice_image
            expense_model.author = request.user
            Raw_Invoice.objects.filter(pk=pk).update(
                date_filed=datetime.now()
            )
            form.save()
            rename_blob(raw_invoice.get_relative_path_to_gcs(), 
                        expense_model.get_relative_path_to_gcs())
            return HttpResponseRedirect(self.success_url)    
        return render(request, self.template_name, {'form': form})
    
