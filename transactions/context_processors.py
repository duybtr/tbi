from .models import Raw_Invoice

def count_invoices(request):
    if request.user.is_authenticated:
        unfiled_invoice_count = Raw_Invoice.objects.filter(date_filed__isnull=True).count()
    else:
        unfiled_invoice_count = 0
    return {
        'unfiled_invoice_count' : unfiled_invoice_count
    }