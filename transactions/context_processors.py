from .models import Raw_Invoice
from .models import Transaction
from django.db.models import Q

def count_unfiled_invoices(request):
    if request.user.is_authenticated:
        unfiled_invoice_count = Raw_Invoice.objects.filter(Q(date_filed__isnull=True) & Q(need_review=False)).count()
    else:
        unfiled_invoice_count = 0
    return {
        'unfiled_invoice_count' : unfiled_invoice_count
    }

def count_review_invoices(request):
    if request.user.is_authenticated:
        review_invoice_count = Raw_Invoice.objects.filter(Q(date_filed__isnull=True) & Q(need_review=True)).count()
    else:
        review_invoice_count = 0
    return {
        'review_invoice_count' : review_invoice_count
    }

def count_transactions(request):
    if request.user.is_authenticated:
        unmatched_transactions_count = Transaction.objects.filter(Q(match_id=0) & Q(is_ignored=False) & Q(transaction_amount__lt=0)).count()
    else:
        unmatched_transactions_count = 0
    return {
        'unmatched_transactions_count' : unmatched_transactions_count
    }