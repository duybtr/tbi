from django.core.management.base import BaseCommand, CommandError
from .gcp_vision_base import *
from .robert_tax_appeals_processor import *
from transactions.models import Raw_Invoice
from datetime import datetime
import common.utils as cmu
from transactions.models import OCR_Invoice_Output
cmu.GCS_ROOT_BUCKET = 'tran_ba_investment_group_llc_test'

def build_source_uri(blob_name):
    return "gs://{}/{}".format(cmu.GCS_ROOT_BUCKET, blob_name)

class Command(BaseCommand):

    def handle(self, *args, **options):
        # list all blobs, and then process them 1 by 1
        raw_invoices = Raw_Invoice.objects.filter(date_filed__isnull = True)
        for ri in raw_invoices:
            #import pdb; pdb.set_trace()
            gcs_source_uri = build_source_uri("unfiled_invoices/"+ ri.invoice_image)
            gcs_destination_uri = "gs://tbi_group_invoice_output/output_files/{}/".format(ri.invoice_image)
            response = async_detect_document(gcs_source_uri, gcs_destination_uri)
            process_detected_text(ri, response)


        # for i,blob in enumerate(cmu.list_blobs('unfiled_invoices/')):
        #     if i == 0: continue
        #     else:
        #         #import pdb; pdb.set_trace()
        #         gcs_source_uri = build_source_uri(blob.name)
        #         file_name = re.match("unfiled_invoices/(\w+)\.\w+", blob.name).group(1)
        #         gcs_destination_uri = "gs://tbi_group_invoice_output/output_files/{}/".format(file_name)
                
        #         response = async_detect_document(gcs_source_uri, gcs_destination_uri)
        #         process_detected_text(response)
                #print(response)
        # gcs_source_uri = "gs://tran_ba_investment_group_llc_test/unfiled_invoices/10647_Hazen_St_invoices_2023_10647_Hazen_Tax_Appeal_2023.pdf"
        # gcs_destination_uri = "gs://tbi_group_invoice_output/output_files/"
        
        # print()
