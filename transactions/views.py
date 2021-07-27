# transactions/views.py

from django.views.generic import TemplateView
import csv, io
from django.shortcuts import render
from django.contrib import messages
from .models import Profile
from .forms import StatementUploadForm
from django.http import HttpResponseRedirect
from django.urls import reverse
import logging


class HomePageView(TemplateView):
    template_name = 'home.html'

class AboutPageView(TemplateView):
    template_name = 'about.html'

def statement_upload(request):
    logging.basicConfig(filename='example.log', level=logging.DEBUG)
    # declaring template
    template = 'transactions/statement_upload.html'
    
    if request.method == "GET":
        form = StatementUploadForm()
        context = {'form':form}
        return render(request, template, context)
    form = StatementUploadForm(request.POST, request.FILES)
    if form.is_valid():
        logging.info(form.cleaned_data['statement_type'])
        logging.info(form.cleaned_data['uploaded_file'])
        csv_file = form.cleaned_data['uploaded_file']
        statement_type = form.cleaned_data['statement_type']
        columns = {}
        if statement_type == 'credit_card':
            logging.info('The user just uploaded a credit_card statement')
        elif statement_type == 'bank':
            logging.info('The user just uploaded a bank statement')
        # let's check if it is a csv file
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'THIS IS NOT A CSV FILE')
        data_set = csv_file.read().decode('UTF-8')
        # setup a stream which is when we loop through each line we are able to handle a data in a stream
        io_string = io.StringIO(data_set)
        next(io_string)
        for column in csv.reader(io_string, delimiter=',', quotechar="|"):
            _, created = Profile.objects.update_or_create(
                name=column[0],
                email=column[1],
                address=column[2],
                phone=column[3],
                profile=column[4]
            )
        return HttpResponseRedirect(reverse('transaction_list'))
def transaction_list(request):
    template = 'transactions/transaction_list.html'
    data = Profile.objects.all()
    context = {'profiles': data }
    return render(request, template, context)
