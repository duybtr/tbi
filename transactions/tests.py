# transactions/tests.py
from django.test import SimpleTestCase, TestCase
from django.urls import reverse, resolve # new
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from .views import HomePageView, StatementCreateView # new
from .models import Transaction, Expense, Revenue, Property, Rental_Unit
from datetime import datetime
from accounts.models import CustomUser
from django.conf import settings
import os


class HomepageTests(SimpleTestCase):

    def setUp(self):
        url = reverse('demo')
        self.response = self.client.get(url)

    # template tests
    def test_homepage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    # def test_homepage_template(self):
    #     self.assertTemplateUsed(self.response, 'home.html')

    # # HTML tests
    # def test_homepage_contains_correct_html(self):
    #     self.assertContains(self.response, 'This is a Home Page')

    # def test_homepage_does_not_contain_incorrect_html(self):
    #     self.assertNotContains(
    #         self.response, 'Hi there! I should not be on the page.')

    # # Make sure the our HomePageView resolves a given url path
    # def test_homepage_url_resolves_homepageview(self): # new
    #     view = resolve('/')
    #     self.assertEqual(
    #         view.func.__name__,
    #         HomePageView.as_view().__name__
    #     )

# class CsvUploadTests(SimpleTestCase):  

#     def setUp(self):
#         url = reverse('upload_csv')
#         self.response = self.client.get(url)

#     def test_csvupload_url(self):
#         self.assertEqual(self.response.status_code, 200)

#     def test_csvupload_template(self):
#         self.assertTemplateUsed(self.response, 'transactions/statement_upload.html')
    
#     def test_csvupload_url_resolves_statementuploadview(self):
#         view = resolve('/upload_statement/')  
#         self.assertEqual(
#             view.func.__name__,
#             statement_upload.__name__
#         )

# class TransactionListTests(TestCase):  

#     def setUp(self):
#         url = reverse('transaction_list')
#         self.response = self.client.get(url)

#     def test_transactionlist_url(self):
#         self.assertEqual(self.response.status_code, 200)

#     def test_transactionlist_template(self):
#         self.assertTemplateUsed(self.response, 'transactions/transaction_list.html')
    
#     def test_transactionlist_url_resolves_transactionlistview(self):
#         view = resolve('/list_transactions/')  
#         self.assertEqual(
#             view.func.__name__,
#             transaction_list.__name__
#         )

# class ExpenseModelTest(TestCase):
#     def setUp(self):
#         User = get_user_model()

#         self.transaction = Transaction.objects.create(
#             transaction_date = datetime.now(),
#             account_number = '1234',
#             statement_type = 'bank',
#             transaction_description = 'Testing',
#             transaction_amount = 23.00,
#             accounting_classification = 'Revenue'
#         )
        

#         self.user = User.objects.create(
#             username = 'superadmin',
#             email = 'admin@gmail.com',
#             password = 12345
#         )

#         self.mock_property = Property.objects.create(
#             address = '123 Elm St',
#             market_price = 1000000.00
#         )
#         self.mock_rental_unit = Rental_Unit.objects.create(
#             address = self.mock_property
#         )
        
#         self.mock_file = SimpleUploadedFile('invoice.txt', b"Hello World")
#         self.mock_expense = Expense.objects.create(
#             record_date = datetime.now(),
#             address = self.mock_rental_unit,
#             expense_type = 'Management Fee',
#             amount = 25.00,
#             document_image = self.mock_file,
#             note = "Testing",
#             author = self.user
#         )

#     def test_get_expense_folder(self):
#         self.assertEqual(
#             self.mock_expense.get_record_folder(),
#             '123_Elm_St/invoices/2021'
#         )
#         os.remove(os.path.join(settings.MEDIA_ROOT, self.mock_file.name))
   
#     def test_expense_content(self):
#         self.assertEqual(self.mock_expense.address.address.address, '123 Elm St')
#         self.assertEqual(self.mock_expense.expense_type, 'Management Fee')
#         self.assertEqual(self.mock_expense.note, 'Testing')
#         self.assertEqual(self.mock_expense.amount, 25.00)

#     def test_expense_list_view(self):
#         response = self.client.get(reverse('expense_list'), args=self.transaction.pk)
#         self.assertEqual(response.status_code, 200)
#         self.assertContains(response, 'Testing')
#         self.assertTemplateUsed(response, 'expense_list.html')


# class RevenueModelTest(TestCase):
#     def setUp(self):
#         User = get_user_model()
#         self.user = User.objects.create(
#             username = 'superadmin',
#             email = 'admin@gmail.com',
#             password = 12345
#         )

#         self.mock_property = Property.objects.create(
#             address = '123 Elm St',
#             market_price = 1000000.00
#         )
#         self.mock_rental_unit = Rental_Unit.objects.create(
#             address = self.mock_property
#         )
        
#         self.mock_file = SimpleUploadedFile('invoice.txt', b"Hello World")
#         self.mock_revenue = Revenue.objects.create(
#             record_date = datetime.now(),
#             address = self.mock_rental_unit,
#             revenue_type = 'rent',
#             amount = 25.00,
#             document_image = self.mock_file,
#             note = "Testing",
#             author = self.user
#         )
#     def test_get_revenue_folder(self):
#         self.assertEqual(
#             self.mock_revenue.get_record_folder(),
#             '123_Elm_St/checks/2021'
#         )
#         os.remove(os.path.join(settings.MEDIA_ROOT, self.mock_file.name))


# class TransactionModelTest(TestCase):
#     def setUp(self):
#         User = get_user_model()
#         self.user = User.objects.create(
#             username = 'superadmin',
#             email = 'admin@gmail.com',
#             password = 12345
#         )

#         self.mock_property = Property.objects.create(
#             address = '123 Elm St',
#             market_price = 1000000.00
#         )
#         self.mock_rental_unit = Rental_Unit.objects.create(
#             address = self.mock_property
#         )
        
#         self.mock_file = SimpleUploadedFile('invoice.txt', b"Hello World")
#         self.mock_expense = Expense.objects.create(
#             expense_date = datetime.now(),
#             address = self.mock_rental_unit,
#             expense_type = 'Management Fee',
#             amount = 25.00,
#             invoice_image = self.mock_file,
#             note = "Testing",
#             author = self.user
#         )
#         self.transaction = Transaction.objects.create(
#             transaction_date = datetime.now(),
#             account_number = '1234',
#             statement_type = 'credit',
#             transaction_description = 'test',
#             transaction_amount = 50.00,
#             match_id = self.mock_expense.id,
#             accounting_classification = 'Revenue',
            
#         )

#     def test_retrieve_matching_expense(self):   
#         transaction = Transaction.objects.get(pk=self.transaction.id) 
#         self.assertEqual(
#             transaction.matching_expense.id,
#             self.mock_expense.id
#         )
#         self.assertTrue(len(self.mock_expense.display_full_path_to_gcs()) > 10)
#         os.remove(os.path.join(settings.MEDIA_ROOT, self.mock_file.name))
