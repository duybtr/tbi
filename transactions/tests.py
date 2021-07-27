# transactions/tests.py
from django.test import SimpleTestCase, TestCase
from django.urls import reverse, resolve # new
from .views import HomePageView, statement_upload, transaction_list# new

class HomepageTests(SimpleTestCase):

    def setUp(self):
        url = reverse('home')
        self.response = self.client.get(url)

    # template tests
    def test_homepage_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_homepage_template(self):
        self.assertTemplateUsed(self.response, 'home.html')

    # HTML tests
    def test_homepage_contains_correct_html(self):
        self.assertContains(self.response, 'This is a Home Page')

    def test_homepage_does_not_contain_incorrect_html(self):
        self.assertNotContains(
            self.response, 'Hi there! I should not be on the page.')

    # Make sure the our HomePageView resolves a given url path
    def test_homepage_url_resolves_homepageview(self): # new
        view = resolve('/')
        self.assertEqual(
            view.func.__name__,
            HomePageView.as_view().__name__
        )

class CsvUploadTests(SimpleTestCase):  

    def setUp(self):
        url = reverse('upload_csv')
        self.response = self.client.get(url)

    def test_csvupload_url(self):
        self.assertEqual(self.response.status_code, 200)

    def test_csvupload_template(self):
        self.assertTemplateUsed(self.response, 'transactions/statement_upload.html')
    
    def test_csvupload_url_resolves_statementuploadview(self):
        view = resolve('/upload_csv/')  
        self.assertEqual(
            view.func.__name__,
            statement_upload.__name__
        )

class TransactionListTests(TestCase):  

    def setUp(self):
        url = reverse('transaction_list')
        self.response = self.client.get(url)

    def test_transactionlist_url(self):
        self.assertEqual(self.response.status_code, 200)

    def test_transactionlist_template(self):
        self.assertTemplateUsed(self.response, 'transactions/transaction_list.html')
    
    def test_transactionlist_url_resolves_transactionlistview(self):
        view = resolve('/list_transactions/')  
        self.assertEqual(
            view.func.__name__,
            transaction_list.__name__
        )