# transactions/views.py

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
import csv, io
from django.shortcuts import render
from django.contrib import messages
from .models import Record, Transaction, Property, Expense, Expense_Category, Revenue, Statement, Raw_Invoice, Document, Rental_Unit
from .forms import StatementUploadForm, TransactionUpdateForm, CreateExpenseForm, UpdateExpenseForm, UpdateRevenueForm, CreateRevenueForm, UploadMultipleInvoicesForm, RawInvoiceUpdateForm, SelectTaxYearForm, UploadDocumentForm
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import UpdateView, CreateView, DeleteView, FormView
from django.views.generic import ListView
from django.views.decorators.http import require_http_methods   
from django.db.models import Q, Value, TextField
from django.db.models.functions import Concat
from django.db import IntegrityError
from common.utils import store_files, format_for_storage, list_blobs, get_full_path_to_gcs, rename_blob, store_in_gcs, GCS_ROOT_BUCKET, delete_file, calculate_file_hash, get_paginator_object
from google.cloud import storage
from django.core.paginator import Paginator
import logging
import google.cloud.logging
from datetime import datetime, timedelta
import os, sys
from decimal import Decimal
from django.conf import settings
from hashlib import md5
from django.core.files.storage import default_storage
#from render_block import render_block_to_string
import gspread


# Initialize logging
# Instantiates a client
client = google.cloud.logging.Client()

# Retrieves a Cloud Logging handler based on the environment
# you're running in and integrates the handler with the
# Python logging module. By default this captures all logs
# at INFO level and higher
client.setup_logging()

class HomePageView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

class AboutPageView(LoginRequiredMixin, TemplateView):
    template_name = 'about.html'

class DemoPageView(TemplateView):
    template_name = 'demo.html'


def convert_date(dt_string):
    return datetime.strptime(dt_string, '%m/%d/%Y').strftime('%Y-%m-%d')
def convert_decimal(amount):
    if not amount:
        return 0
    return amount

class StatementCreateView(LoginRequiredMixin, CreateView):
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

class StatementListView(LoginRequiredMixin, ListView):
    model = Statement
    context_object_name = 'statements'
    template = 'transactions/statement_list.html'
    ordering = ['statement_type', 'account_number', 'period_ending_date']

class StatementDeleteView(LoginRequiredMixin, DeleteView):
    model = Statement
    # not sure why this doesn't work
    # template = 'transactions/statement_delete.html' 
    context_object_name = 'statement'
    success_url = reverse_lazy('statement_list')
        
    def delete(self, *args, **kwargs):
        statement = Statement.objects.get(pk=self.kwargs.get('pk'))
        if statement.uploaded_file.name:
            delete_file(statement.uploaded_file.name, statement.get_statement_folder())
        return super(StatementDeleteView, self).delete(*args, **kwargs)
class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    context_object_name = 'transactions'
    template_name = 'transactions/transaction_list_ajax.html'

    def get_context_data(self, **kwargs):
        context = {}
        curr_year = datetime.now().year 
        context['years'] = list(range(curr_year, curr_year-5, -1))
        context['target_url'] = '/get_transaction_list' # for the inital ajax call
        return context

class UnmatchedTransactionListView(TransactionListView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_url'] = '/get_unmatched_transaction_list' # for the inital ajax call
        return context

class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction 
    form_class  = TransactionUpdateForm
    template_name = 'transactions/transaction_edit.html'
    #success_url = reverse_lazy('transaction_list')

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
        next_string = request.POST.get('next', '/')
        if form.is_valid():
            updated_transaction = form.save(commit=False)
            transaction.is_ignored = updated_transaction.is_ignored
            transaction.transaction_description = updated_transaction.transaction_description
            transaction.save()
            return HttpResponseRedirect(next_string)  
        return render(request, self.template_name, {'form': form})
class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = 'transactions/transaction_delete.html'
    success_url = reverse_lazy('transaction_list')

class CreateExpenseView(LoginRequiredMixin, CreateView):
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

class CreateRevenueView(LoginRequiredMixin, CreateView):
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

class UploadDocumentView(LoginRequiredMixin, CreateView):
    model = Document
    form_class = UploadDocumentForm
    template_name = 'transactions/document_upload.html'
    success_url = reverse_lazy('upload_document')

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            document_model = form.save(commit=False)
            document_model.author = request.user
            if document_model.document_image.name:
                store_in_gcs([document_model.document_image], GCS_ROOT_BUCKET, document_model.get_record_folder())
            form.save()
            if document_model.document_image.name:
                os.remove(os.path.join(settings.MEDIA_ROOT, document_model.document_image.name))
            return HttpResponseRedirect(self.success_url)    
        return render(request, self.template_name, {'form': form})


class CreateMatchingRevenueView(LoginRequiredMixin, CreateView):
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

class CreateMatchingExpenseView(LoginRequiredMixin, CreateView):
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

class ExpenseListView(LoginRequiredMixin, TemplateView):
    template_name = 'transactions/expense_list.html'
   
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        addresses = Property.objects.all().order_by('address')
        curr_year = datetime.now().year 
        category_objs = Expense_Category.objects.all()
        categories = [c['expense_category'] for c in category_objs.values('expense_category')]
        context['categories'] = categories
        context['addresses'] = addresses
        context['years'] = list(range(curr_year, curr_year-5, -1))
        context['target_url'] = 'get_expense_list'
        return context

class DocumentListView(LoginRequiredMixin, ListView):
    model = Document
    template_name = 'transactions/document_list.html'
    context_object_name = 'documents'
    paginate_by = 50

class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = Document
    template_name = 'transactions/document_delete.html'
    success_url = reverse_lazy('upload_document')

    def delete(self, *args, **kwargs):
        document = Document.objects.get(pk=self.kwargs.get('pk'))
        if document.document_image.name:
            delete_file(document.document_image.name, document.get_record_folder())
        return super(DocumentDeleteView, self).delete(*args, **kwargs)


class RevenueListView(LoginRequiredMixin, TemplateView):
    template_name = 'transactions/revenue_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        addresses = Property.objects.all().order_by('address')
        curr_year = datetime.now().year 
        context['addresses'] = addresses
        context['years'] = list(range(curr_year, curr_year-5, -1))
        context['target_url'] = 'get_revenue_list'
        return context

class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    model = Expense
    form_class = CreateExpenseForm
    template_name = 'transactions/expense_edit.html'
    success_url = reverse_lazy('expense_list')

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        previous_expense = Expense.objects.get(pk=self.kwargs.get('pk'))
        updated_expense = form.save(commit=False)
        updated_expense.author = request.user
        next_string = request.POST.get('next', '/')
        if form.is_valid():
            return HttpResponseRedirect(next_string)  
        return render(request, self.template_name, {'form': form})
  

class RevenueUpdateView(LoginRequiredMixin, UpdateView):
    model = Revenue
    form_class = CreateRevenueForm
    template_name = 'transactions/revenue_edit.html'
    success_url = reverse_lazy('revenue_list')
 

class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    template_name = 'transactions/expense_delete.html'
    success_url = reverse_lazy('expense_list')

    def delete(self, *args, **kwargs):
        expense = Expense.objects.get(pk=self.kwargs.get('pk'))
        if expense.document_image.name:
            delete_file(expense.document_image.name, expense.get_record_folder())
        Transaction.objects.filter(match_id=self.kwargs.get('pk')).update(match_id = 0)
        return super(ExpenseDeleteView, self).delete(*args, **kwargs)

class RevenueDeleteView(LoginRequiredMixin, DeleteView):
    model = Revenue
    template_name = 'transactions/revenue_delete.html'
    success_url = reverse_lazy('revenue_list')

    def delete(self, *args, **kwargs):
        revenue = Revenue.objects.get(pk=self.kwargs.get('pk'))
        if revenue.document_image.name:
            delete_file(revenue.document_image.name, revenue.get_record_folder())
        Transaction.objects.filter(match_id=self.kwargs.get('pk')).update(match_id = 0)
        return super(RevenueDeleteView, self).delete(*args, **kwargs)

class MatchingExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'transactions/matching_expense_list.html'

    def get(self, request, *args, **kwargs):
        q = Q()
        context = {}
        #logging.info('kwargs {}'.format(self.kwargs.get('pk')))
        target_transaction = Transaction.objects.get(pk=self.kwargs.get('pk'))
        target_date = target_transaction.transaction_date
        date_range = [(target_date - timedelta(days=90)).strftime('%Y-%m-%d'),
                      (target_date + timedelta(days=90)).strftime('%Y-%m-%d')]
        
        matched_expenses = Transaction.objects.filter(
            transaction_amount__lt = 0
        ).values_list('match_id', flat=True)
        target_transaction_amount_upper = -1*(target_transaction.transaction_amount * Decimal(1.1))
        target_transaction_amount_lower = -1*(target_transaction.transaction_amount * Decimal(0.9))
        context['target_transaction'] = target_transaction
        request.session['transaction_pk'] = target_transaction.pk
        q = q & Q(record_date__range = date_range)
        q = q & Q(amount__lte = target_transaction_amount_upper) & Q(amount__gte = target_transaction_amount_lower)
        context['object_list'] = Expense.objects.filter(q).exclude(id__in=matched_expenses)
        return render(request, self.template_name, context)
    

class MatchingRevenueListView(LoginRequiredMixin, ListView):
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

class UploadMultipleInvoicesView(LoginRequiredMixin, FormView):
    form_class = UploadMultipleInvoicesForm
    template_name = 'transactions/upload_multiple_invoices.html'
    success_url = reverse_lazy('upload_multiple_invoices')
    
    def get(self, request, *args, **kwargs):
        context = {}
        successful_uploads = request.session.get('successful_uploads', [])
        failed_uploads = request.session.get('failed_uploads', [])
        selected_tax_year = request.session.get('selected_tax_year', datetime.now().year)
        form_class = self.get_form_class()

        form = self.form_class(initial={
            'tax_year' : selected_tax_year
        })

        
        context['successful_uploads'] = successful_uploads
        context['failed_uploads'] = failed_uploads  
        context['form'] = form
        request.session['successful_uploads'] = []
        request.session['failed_uploads'] = []
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        directory = 'unfiled_invoices'
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('invoices')
        successful_uploads = []
        failed_uploads = []
        if form.is_valid():
            tax_year = form.cleaned_data['tax_year']
            for f in files:
                logging.info("Attempting to store file {}".format(f.name))
                tmp_file_name = format_for_storage(f.name)
                default_storage.save(tmp_file_name, f)
                full_file_path = settings.MEDIA_ROOT + '/' + tmp_file_name
                with open(full_file_path, "rb") as current_file:
                    try:
                        invoice = Raw_Invoice.objects.create(
                            upload_date = datetime.now(),
                            invoice_image = tmp_file_name,
                            author = request.user,
                            tax_year = int(tax_year),
                            file_hash = calculate_file_hash(current_file)
                        )
                        successful_uploads.append(f.name)    
                        current_file.seek(0)
                        store_in_gcs([current_file], GCS_ROOT_BUCKET, directory)
                        invoice.save()
                    except IntegrityError as e:
                        if "duplicate key" in str(e):
                            logging.info("File {} has already been uploaded.".format(f.name))
                            failed_uploads.append(f.name)
                os.remove(full_file_path)
                      
            request.session['successful_uploads'] = successful_uploads
            request.session['failed_uploads'] = failed_uploads
            request.session['selected_tax_year'] = tax_year
            return HttpResponseRedirect(self.success_url)
        else:
            return render(request, self.template_name, {'form': form})

class RawInvoiceListView(LoginRequiredMixin, ListView):
    model = Raw_Invoice
    template_name = 'transactions/raw_invoice_list.html'
    success_url = reverse_lazy('raw_invoices')
    paginate_by = 50

    def get_queryset(self):
        return Raw_Invoice.objects.filter(Q(date_filed__isnull=True) & Q(need_review=False)).order_by("-upload_date")

class ReviewInvoiceListView(LoginRequiredMixin, ListView):
    model = Raw_Invoice
    template_name = 'transactions/raw_invoice_list.html'
    success_url = reverse_lazy('raw_invoices')
    paginate_by = 50

    def get_queryset(self):
        return Raw_Invoice.objects.filter(Q(date_filed__isnull=True) & Q(need_review=True))

class ReviewInvoiceEditView(LoginRequiredMixin, UpdateView):
    model = Raw_Invoice
    form_class = RawInvoiceUpdateForm
    template_name = 'transactions/raw_invoice_edit.html'
    success_url = reverse_lazy('review_invoices')

class RawInvoiceEditView(LoginRequiredMixin, UpdateView):
    model = Raw_Invoice
    form_class = RawInvoiceUpdateForm
    template_name = 'transactions/raw_invoice_edit.html'
    success_url = reverse_lazy('raw_invoices')

class RawInvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Raw_Invoice
    template_name = 'transactions/raw_invoice_delete.html'
    success_url = reverse_lazy('raw_invoices')

    def delete(self, *args, **kwargs):
        raw_invoice = Raw_Invoice.objects.get(pk=self.kwargs.get('pk'))
        if raw_invoice.invoice_image:
            delete_file(raw_invoice.invoice_image.name, Raw_Invoice.directory)
        return super(RawInvoiceDeleteView, self).delete(*args, **kwargs)

class FileInvoiceView(LoginRequiredMixin, UpdateView):
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
            expense_model.document_hash = raw_invoice.file_hash
            Raw_Invoice.objects.filter(pk=pk).update(
                date_filed=datetime.now()
            )
            form.save()
            rename_blob(raw_invoice.get_relative_path_to_gcs(), 
                        expense_model.get_relative_path_to_gcs())
            return HttpResponseRedirect(self.success_url)    
        return render(request, self.template_name, {'form': form})

class GetTaxReportView(LoginRequiredMixin, FormView):
    form_class = SelectTaxYearForm
    template_name = "transactions/get_tax_report.html"
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            tax_year = form.cleaned_data['tax_year']
            gc = gspread.service_account(filename='cloud_keys/tbi-finance-a3f1a4fd0be6.json')
            report_name = 'Tran Ba Investment Group Tax Report ' + tax_year
            sh = gc.open(report_name)
            redirect_url = "https://docs.google.com/spreadsheets/d/{}".format(sh.id)
            return HttpResponseRedirect(redirect_url)
        return render(request, self.template_name, {'form': form})

def get_suites(request):
    address = request.GET.get('address')
    rental_units = Rental_Unit.objects.filter(address__address=address).exclude(suite='').order_by('suite')
    # return empty html requests
    if len(rental_units) != 0:
        return render(request, 'transactions/partial/suite_list.html', {'rental_units': rental_units})
    else:
        return HttpResponse()

def get_revenue_list(request):
    q = Q()
    query = request.GET.get('q')
    order_by = request.GET.get('order_by')
    current_year = request.GET.get('year')
    queryset = Revenue.objects.all()
    address = request.GET.get('address')
    suite = request.GET.get('suite')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')


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
    if start_date:
        q = q & Q(record_date__gte = start_date)
    if end_date:
        q = q & Q(record_date__lte = end_date)
    if not current_year or current_year == 'all':
        q = q & Q(record_date__year__lte = datetime.now().year)
    else:
        q = q & Q(record_date__year = current_year)
    if order_by is None:
        order_by = '-record_date'
    if address and address != 'all':
        q = q & Q(address__address__address = address)
    if suite and suite != 'all':
        q = q & Q(address__suite = suite)

   
    
    order_by_dict = {'-record_date' :['-record_date', 'address_and_suite'],
                        '-date_filed': ['-date_filed', 'address_and_suite'],
                        'address' : ['address_and_suite', '-date_filed']
                    }
    
    results = queryset.filter(q).order_by(*order_by_dict[order_by])
    context = {}
    page_obj = get_paginator_object(results, 50, request)
    context['page_obj'] = page_obj
    context['target_url'] = 'get_revenue_list'
    return render(request, 'transactions/partial/revenue_list.html', context)       
def get_expense_edit(request, expense_pk):
    expense = Expense.objects.get(pk=expense_pk)
    context = {}
    context['expense'] = expense
    context['form'] = UpdateExpenseForm(initial={
        'record_date':expense.record_date,
        'address': expense.address,
        'expense_category': expense.expense_category,
        'document_image': expense.document_image,
        'amount': expense.amount,
        'note': expense.note
    })
    
    return render(request, 'transactions/partial/expense_edit.html', context)

def edit_matching_expense(request, transaction_pk, expense_pk):
    expense = Expense.objects.get(pk=expense_pk)
    target_transaction = Transaction.objects.get(pk = transaction_pk)
    context = {}
    context['expense'] = expense
    context['target_transaction'] = target_transaction
    context['form'] = UpdateExpenseForm(initial={
        'record_date':expense.record_date,
        'address': expense.address,
        'expense_category': expense.expense_category,
        'amount': expense.amount,
        'note': expense.note
    })
    return render(request, 'transactions/partial/edit_matching_expense.html', context)

@require_http_methods(["GET", "POST"])
def get_matching_expense_row(request, expense_pk):
    context = {}
    transaction_pk = request.session.get('transaction_pk', None)
    target_transaction = Transaction.objects.get(pk = transaction_pk)
    context['target_transaction'] = target_transaction
    expense = Expense.objects.get(pk=expense_pk)
    if request.method == 'POST':
        form = UpdateExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
        else:
            return render(request, 'transactions/partial/edit_matching_expense.html', context)
    context['expense'] = expense
    return render(request, 'transactions/partial/matching_expense_row.html', context)

def get_revenue_edit(request, revenue_pk):
    revenue = Revenue.objects.get(pk=revenue_pk)
    context = {}
    context['revenue'] = revenue
    context['form'] = UpdateRevenueForm(initial={
        'record_date':revenue.record_date,
        'address': revenue.address,
        'revenue_type': revenue.revenue_type,
        'amount': revenue.amount,
        'note': revenue.note

    })
    return render(request, 'transactions/partial/revenue_edit.html', context)

def add_revenue(request):
    context = {}
    context['form'] = CreateRevenueForm()
    return render(request, 'transactions/partial/add_revenue.html', context)

def add_expense(request):
    context = {}
    context['form'] = CreateExpenseForm()
    return render(request, 'transactions/partial/add_expense.html', context)
# Unlike the edit flow, in which hitting cancel returns an unmodified row, in the 'add new record' flow, there is no previous row to return to    
def cancel_new_record(request):
    return HttpResponse()
def delete_revenue(request, revenue_pk):
    revenue = Revenue.objects.get(pk=revenue_pk)
    revenue.delete()
    return HttpResponse()
def delete_expense(request, expense_pk):
    expense = Expense.objects.get(pk=expense_pk)
    if expense.document_image.name:
        delete_file(expense.document_image.name, expense.get_record_folder())
    Transaction.objects.filter(match_id=expense_pk).update(match_id = 0)
    expense.delete()
    return HttpResponse()

@require_http_methods(["GET", "POST"])    
def add_revenue_submit(request):
    context = {}
    if request.method == 'POST':
        form = CreateRevenueForm(request.POST)
        if form.is_valid():
            revenue = form.save(commit=False)
            revenue.author = request.user
            form.save()
            context['revenue'] = revenue
        else:
            return render(request, 'transactions/partial/add_revenue.html', context)
    return render(request, 'transactions/partial/revenue_row.html', context)

def store_expense_invoice(expense):
    tmp_file_name = format_for_storage(expense.document_image.name)
    full_file_path = settings.MEDIA_ROOT + '/' + tmp_file_name
    with open(full_file_path, "rb") as current_file:
        store_in_gcs([current_file], GCS_ROOT_BUCKET, expense.get_record_folder())
    os.remove(os.path.join(settings.MEDIA_ROOT, expense.document_image.name))

def add_expense_submit(request):
    context = {}
    if request.method == 'POST':
        form = CreateExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.author = request.user
            form.save() 
            context['expense'] = expense
            if expense.document_image.name:
                store_expense_invoice(expense)
        else:
            return render(request, 'transactions/partial/add_expense.html', context)
    return render(request, 'transactions/partial/expense_row.html', context)

@require_http_methods(["GET", "POST"])
def get_revenue_row(request, revenue_pk=None):
    context = {}
    revenue = Revenue.objects.get(pk=revenue_pk)
    if request.method == 'POST':
        form = UpdateRevenueForm(request.POST, instance=revenue)
        if form.is_valid():
            form.save()
        else:
            return render(request, 'transactions/partial/revenue_edit.html', context)
    context['revenue'] = revenue
    return render(request, 'transactions/partial/revenue_row.html', context)

@require_http_methods(["GET", "POST"])
def get_expense_row(request, expense_pk):
    context = {}
    expense = Expense.objects.get(pk=expense_pk)
    if request.method == 'POST':
        previous_invoice = expense.document_image.name
        form = UpdateExpenseForm(request.POST, request.FILES, instance=expense)
        if form.is_valid():
            form.save()
            if len(request.FILES) > 0:
                store_expense_invoice(expense)
                delete_file(previous_invoice, expense.get_record_folder())    
        else:
            return render(request, 'transactions/partial/expense_edit.html', context)
    context['expense'] = expense
    return render(request, 'transactions/partial/expense_row.html', context)

def initialize_matching_expense_form(request):
    transaction_pk = request.session.get('transaction_pk', None)
    target_transaction = Transaction.objects.get(pk = transaction_pk)
    form = CreateExpenseForm(initial={
        'record_date':target_transaction.transaction_date, 
        'amount':-1*target_transaction.transaction_amount, 
        'note':target_transaction.transaction_description
    })     
    return form

@require_http_methods(["GET", "POST"])
# this method creating a new expense and match it with the target trasaction
def add_matching_expense_submit(request):
    import pdb; pdb.set_trace()
    context = {}
    transaction_pk = request.session.get('transaction_pk', None)
    if request.method == 'POST':
        form = CreateExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.author = request.user
            form.save()
            if len(request.FILES) > 0:
                store_expense_invoice(expense)
            Transaction.objects.filter(pk=transaction_pk).update(match_id=expense.pk)
        else:
            context['form'] = form
            return render(request, 'transactions/partial/add_matching_expense.html', context)
    response = HttpResponse()
    response["HX-Redirect"] = reverse_lazy('unmatched_transaction_list')
    return response

def get_expense_list(request):
    q = Q()
    query = request.GET.get('q')
    order_by = request.GET.get('order_by')
    current_year = request.GET.get('year')
    address = request.GET.get('address')
    suite = request.GET.get('suite')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    unmatched_invoice = request.GET.get('unmatched_invoice')
    category = request.GET.get('category')

    queryset = Expense.objects.all()
    if not query is None:
        queryset = queryset.annotate(searchable_text=Concat('address__address__address', Value(' '), 'address__suite', Value(' '), 'expense_category__expense_category', Value(' '), 'note', output_field=TextField()))

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

    if start_date:
        q = q & Q(record_date__gte = start_date)
    if end_date:
        q = q & Q(record_date__lte = end_date)
    if not current_year or current_year == 'all':
        q = q & Q(record_date__year__lte = datetime.now().year)
    else:
        q = q & Q(record_date__year = current_year)
    if address and address != 'all':
        q = q & Q(address__address__address = address)
    if suite and suite != 'all':
        q = q & Q(address__suite = suite)
    if category and category != 'all':
        q = q & Q(expense_category__expense_category = category)

    query = request.GET.get('q')
    
    order_by_dict = {'-record_date' :['-record_date', 'address_and_suite'],
                        '-date_filed': ['-date_filed', 'address_and_suite'],
                        'address' : ['address_and_suite', '-date_filed'],
                        'amount' : ['-amount','-record_date']}

    queryset = queryset.annotate(address_and_suite=Concat('address__address__address', Value(' '), 'address__suite', output_field=TextField()))
    queryset = queryset.filter(q).order_by(*order_by_dict[order_by])
    page_obj = get_paginator_object(queryset, 50, request)
    context = {}
    context['page_obj'] = page_obj
    context['target_url'] =  'get_expense_list'
    return render(request, 'transactions/partial/expense_list.html', context)

def setup_transaction_filters(request):
    q = Q()
    query = request.GET.get('q')
    statement_id = request.GET.get('statement_id')
    start_date = request.GET.get('start_date')
    
    current_year = request.GET.get('year')
    if not start_date:
        start_date = '2008-01-01' 
    end_date = request.GET.get('end_date')
    if not end_date:
        end_date = datetime.now()
    q = Q(transaction_date__range=[start_date, end_date])
    if not current_year or current_year == 'all':
        q = q & Q(transaction_date__year__lte = datetime.now().year)
    else:
        q = q & Q(transaction_date__year = current_year)

    if not query is None:
        try:
            target_amount = float(query)
            lower,upper = sorted((0.9*target_amount, 1.1*target_amount))
            q = q & Q(transaction_amount__gte=lower) & Q(transaction_amount__lte=upper)
            q = q | Q(transaction_description__icontains=query)
        except ValueError:
            q = q & Q(transaction_description__icontains=query)
    return q

def get_transaction_list(request):
    order_by = request.GET.get('order_by')
    q = setup_transaction_filters(request)
    if order_by is None:
        order_by = '-transaction_date'
    queryset = Transaction.objects.filter(q).order_by('-transaction_date', 'statement__statement_type', 'statement__account_number')
    context = {}
    page_obj = get_paginator_object(queryset, 50, request)
    context['page_obj'] = page_obj
    context['target_url'] = '/get_transaction_list' # for pagination
    return render(request, 'transactions/partial/transaction_list.html', context)

def get_unmatched_transaction_list(request):
    order_by = request.GET.get('order_by')
    q = setup_transaction_filters(request)
    q = q & Q(match_id=0) & Q(is_ignored=False) & Q(transaction_amount__lt=0)
    if order_by is None:
        order_by = '-transaction_date'
    queryset = Transaction.objects.filter(q).order_by('-transaction_date', 'statement__statement_type', 'statement__account_number')
    context = {}
    page_obj = get_paginator_object(queryset, 50, request)
    context['page_obj'] = page_obj
    context['target_url'] = '/get_unmatched_transaction_list' # for pagination
    return render(request, 'transactions/partial/transaction_list.html', context)

def get_transaction_edit(request, transaction_pk):
    transaction = Transaction.objects.get(pk=transaction_pk)
    context = {}
    context['transaction'] = transaction
    context['form'] = TransactionUpdateForm(initial={
        'transaction_description' : transaction.transaction_description
    })    
    return render(request, 'transactions/partial/transaction_edit.html', context)

@require_http_methods(["GET", "POST"])
def get_transaction_row(request, transaction_pk):
    context = {}
    transaction = Transaction.objects.get(pk=transaction_pk)
    context['transaction'] = transaction
    if request.method == 'POST':
        if 'unmatch_invoice' in request.POST.keys() and request.POST['unmatch_invoice'] == 'on':
            Transaction.objects.filter(pk=transaction_pk).update(match_id=0)
            transaction.refresh_from_db()

        form = TransactionUpdateForm(request.POST, instance=transaction)
        context['form'] = form
        if form.is_valid():
            form.save()
        else:
            return render(request, 'transactions/partial/transaction_edit.html', context)
    return render(request, 'transactions/partial/transaction_row.html', context)

def delete_transaction(request, transaction_pk):
    context = {}
    transaction = Transaction.objects.get(pk=transaction_pk)
    transaction.delete()
    return HttpResponse()

def add_matching_expense(request):
    context = {}
    form = initialize_matching_expense_form(request) 
    context['form'] = form
    return render(request, 'transactions/partial/add_matching_expense.html', context)

def get_test_form(request):
    context = {}
    queryset = Expense.objects.all()
    return HttpResponse()

