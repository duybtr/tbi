from django.core.management.base import BaseCommand, CommandError
from .gcp_vision_base import *
from .robert_tax_appeals_processor import *

class Command(BaseCommand):
    def handle(self, *args, **options):
        gcs_source_uri = "gs://tran_ba_investment_group_llc/14258_Valverde_Point_Ln/invoices/2023/14258_Valverde_Point_Tax_Appeal_2023.pdf"
        gcs_destination_uri = "gs://tran_ba_investment_group_llc/14258_Valverde_Point_Tax_Appeal_2023"
        response = async_detect_document(gcs_source_uri, gcs_destination_uri)
        print(process_detected_text(response))
