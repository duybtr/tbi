from datetime import date
from decimal import *
from transactions.models import *
from accounts.models import *
from django.core.files.uploadedfile import SimpleUploadedFile
from google.cloud import storage
import common.utils as cmu
cmu.GCS_ROOT_BUCKET = 'tran_ba_investment_group_llc_test'
import locale
import re
locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )
import logging
import google.cloud.logging


client = google.cloud.logging.Client()
client.setup_logging()


def extract_date(target):
    try:
        match = re.search("Date\\n\d{5}\\n(\d{1,2}\/\d{1,2}\/\d{4})", target).group(1)
        month, day, year = match.split("/")
        return date(int(year), int(month), int(day))
    except (ValueError, AttributeError) as e:
        logging.critical(e)

def extract_invoice_amount(target):
    try:
        match = re.search("\\n\d{1,2}\%(?s).*\\n\$(\d{0,3},{0,1}\d{1,3}\.\d{1,2})", target).group(1)
        return locale.atof(match, func=Decimal)
    except AttributeError as e: 
        logging.critical(e) 
    except Exception as e:
        logging.critical(e) 
        raise
    
def extract_address(target):
    try: 
        rental_units = Rental_Unit.objects.all()
        ru_dicts = {(ru.address.address + ' ' + ru.suite).strip() :ru for ru in rental_units}
        match = re.search("RE: (\d+ .+) \d{4} tax year", target)
        address_extract = match.group(1).strip(".")
        if "mckinney" in address_extract.lower():
            street_number, street_name, street_suffix = address_extract.strip().split(" ")
            address_extract = f'4102-4116 {street_name} {street_suffix} {street_number}'
        elif "n breen" in  address_extract.lower():
            address_extract = "7303 Breen Dr"
        rental_unit = ru_dicts[address_extract]
        return rental_unit
    except AttributeError as e: 
        logging.critical(e) 
    except Exception as e:
        logging.critical(e) 
        raise

def extract_note(target):
    return re.search("\\n(RE: .+ acct \# \d+)", target).group(1)

def get_raw_text(response):
    first_page_response = response["responses"][0]
    annotation = first_page_response["fullTextAnnotation"]         
    raw_text = annotation["text"]
    return raw_text

def process_detected_text(raw_invoice, response):      
    raw_text = get_raw_text(response)
    if "www.RobertsTaxAppeals.com" in raw_text:
        text_list = raw_text.split("\n")
        invoice_uri = response['inputConfig']['gcsSource']['uri'].split('/')
        invoice_file_name = invoice_uri[-1]
        path_to_file = '/'.join(invoice_uri[3:])
        gcp_vision_user = CustomUser.objects.filter(username='gcp_vision')
        # move the file to the appropriate directory
        #import pdb; pdb.set_trace()
        expense_category = Expense_Category.objects.filter(expense_category="Misc")[0]
        expense = Expense.objects.create(
            record_date = extract_date(raw_text),
            amount = extract_invoice_amount(raw_text),
            address = extract_address(raw_text),
            expense_category = expense_category,
            document_image = SimpleUploadedFile(invoice_file_name, b""),
            raw_invoice = raw_invoice, 
            note = extract_note(raw_text),
            author = gcp_vision_user[0]
        )
        raw_invoice.date_filed = datetime.now()
        raw_invoice.save()
        cmu.rename_blob(path_to_file, expense.get_relative_path_to_gcs())
        
    return expense

   
