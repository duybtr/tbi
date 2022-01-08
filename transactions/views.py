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
from django.db.models import Q, Value
from django.db.models.functions import Concat
from common.utils import store_files, list_blobs, get_full_path_to_gcs, rename_blob, store_in_gcs, GCS_ROOT_BUCKET, delete_file
from google.cloud import storage
import logging
import google.cloud.logging
from datetime import datetime
import os, sys
from decimal import Decimal
from django.conf import settings

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
    template = 'transactions/transaction_list.html'
    paginate_by = 50

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
        return Transaction.objects.filter(q).order_by('statement__statement_type', 'statement__account_number', 'transaction_date')

class UnmatchedTransactionListView(ListView):
    model = Transaction
    context_object_name = 'transactions'
    template = 'transactions/transaction_list.html'
    paginate_by = 50

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
        q = q & Q(match_id=0)
        return Transaction.objects.filter(q).order_by('statement__statement_type', 'statement__account_number', 'transaction_date')

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
    success_url = reverse_lazy('revenue_list')

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

class ExpenseListView(ListView):
    model = Expense
    template_name = 'transactions/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 50
    ordering = ['id']

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query is None:
            return Expense.objects.all()
        else:
            queryset = Expense.objects.annotate(full_address=Concat('address__address__address', Value(' '), 'address__suite'))
            return queryset.filter(
                Q(full_address__icontains=query) | Q(note__icontains=query) | Q(expense_type__icontains=query)
            )
            
class RevenueListView(ListView):
    model = Revenue
    template_name = 'transactions/revenue_list.html'
    context_object_name = 'revenues'
    paginate_by = 50

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query is None:
            return Revenue.objects.all()
        else:
            return Revenue.objects.filter(
                Q(address__address__address__icontains=query) | Q(note__icontains=query) 
            )

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
        target_transaction_amount_upper = -1*(target_transaction.transaction_amount * Decimal(1.2))
        target_transaction_amount_lower = -1*(target_transaction.transaction_amount * Decimal(0.8))
        context['target_transaction'] = target_transaction
        context['object_list'] = Expense.objects.filter(
            amount__lte=target_transaction_amount_upper
        ).filter(
            amount__gte=target_transaction_amount_lower
        ).exclude(
            id__in=matched_expenses
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
        target_transaction_amount_upper = target_transaction.transaction_amount * Decimal(1.2)
        target_transaction_amount_lower = target_transaction.transaction_amount * Decimal(0.8)
        context['target_transaction'] = target_transaction
        context['object_list'] = Revenue.objects.filter(
            amount__lte=target_transaction_amount_upper
        ).filter(
            amount__gte=target_transaction_amount_lower
        ).exclude(
            id__in=matched_revenues
        )
        return context
    
def match_expense(request, transaction_pk, expense_pk):
    #logging.info("Transaction pk: {} -  Expense pk: {}".format(transaction_pk, expense_pk))
    matching_expense = Expense.objects.get(pk=expense_pk)
    Transaction.objects.filter(pk=transaction_pk).update(match_id=expense_pk)
    return HttpResponseRedirect(reverse('transaction_list'))

def match_revenue(request, transaction_pk, revenue_pk):
    #logging.info("Transaction pk: {} -  Revenue pk: {}".format(transaction_pk, revenue_pk))
    matching_revenue = Revenue.objects.get(pk=revenue_pk)
    Transaction.objects.filter(pk=transaction_pk).update(match_id=revenue_pk)
    return HttpResponseRedirect(reverse('transaction_list'))

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
            for f in files:
                invoice = Raw_Invoice.objects.create(
                    upload_date = datetime.now(),
                    invoice_image = f,
                    author = request.user
                )
                full_file_path = settings.MEDIA_ROOT + '/' + f.name
                with open(full_file_path, "rb") as my_file:
                    store_in_gcs([my_file], GCS_ROOT_BUCKET, directory)
                invoice.save()
                os.remove(full_file_path)

            return self.form_valid(form)
        else:
            return self.form_invalid(form)

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

class FileInvoiceView(UpdateView):
    model = Expense
    form_class = CreateExpenseForm
    success_url = reverse_lazy('expense_list')
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
