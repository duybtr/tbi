from datetime import date
from decimal import *
from transactions.models import *
from django.core.files.uploadedfile import SimpleUploadedFile
from google.cloud import storage
import locale
import re
locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )

def process_date(date_string):
    if date_string.replace("/","").isdigit():
        month, day, year = date_string.split("/")
        return date(int(year), int(month), int(day))
    else:
        raise Exception("Expected a date field in the format mm/dd/yyyy. Got {}.".format(date_string))

def process_invoice_amount(amount_string):
    return locale.atof(amount_string.strip("$"), func=Decimal)

def process_address(address_str):
    addresses = Rental_Unit.objects.all()
    rental_units = list(addresses.values('id', 'address__address', 'suite'))
    ru_dicts = {(ru['address__address'] + ' ' + ru['suite']).strip() :ru['id'] for ru in rental_units}
    match = re.match("RE: (\d+ .+) \d{4} tax year", address_str)
    address_extract = match.group(1).strip(".")
    rental_unit_id = ru_dicts[address_extract.strip()]
    return rental_unit_id

def process_detected_text(response):
    first_page_response = response["responses"][0]
    annotation = first_page_response["fullTextAnnotation"]         
    raw_text = annotation["text"]
    if "www.RobertsTaxAppeals.com" in raw_text:
        text_list = raw_text.split("\n")
        record_date = process_date(text_list[35])         
        record_amount = process_invoice_amount(text_list[29])
        rental_unit_id = process_address(text_list[5])
        note = text_list[19] + ' ' + text_list[5]
        invoice_uri = response['inputConfig']['gcsSource']['uri'].split('/')
        invoice_file_name = invoice_uri[-1]
        path_to_file = '/'.join(invoice_uri[3:])

        client = storage.Client()
        bucket = client.get_bucket(bucket_name)
        bucket.blob(path_to_file)
        expense = Expense.object.create(
            record_date = process_date(text_list[35]),
            amount = process_invoice_amount(text_list[29]),
            address = process_address(text_list[5]),
            document_image = 
            note = text_list[19] + ' ' + text_list[5]

        )
    return record_date, record_amount, rental_unit_id, note

   
