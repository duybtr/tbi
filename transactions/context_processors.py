from .models import Raw_Invoice
from .models import Transaction

def count_invoices(request):
    if request.user.is_authenticated:
        unfiled_invoice_count = Raw_Invoice.objects.filter(date_filed__isnull=True).count()
    else:
        unfiled_invoice_count = 0
    return {
        'unfiled_invoice_count' : unfiled_invoice_count
    }

def count_transactions(request):
    if request.user.is_authenticated:
        unmatched_transactions_count = Transaction.objects.filter(match_id=0).count()
    else:
        unmatched_transactions_count = 0
    return {
        'unmatched_transactions_count' : unmatched_transactions_count
    }