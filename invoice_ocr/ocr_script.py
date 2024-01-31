import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.prod')
django.setup()
from transactions.models import *


from gcp_vision_base import async_detect_document

gcs_source_uri = "gs://tran_ba_investment_group_llc/14258_Valverde_Point_Ln/invoices/2023/14258_Valverde_Point_Tax_Appeal_2023.pdf"
gcs_destination_uri = "gs://tran_ba_investment_group_llc/14258_Valverde_Point_Tax_Appeal_2023"
response = async_detect_document(gcs_source_uri, gcs_destination_uri)
first_page_response = response["responses"][0]
annotation = first_page_response["fullTextAnnotation"]         
raw_text = annotation["text"]