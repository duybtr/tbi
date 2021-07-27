# transactions/urls.py

from django.urls import path
from .views import HomePageView, AboutPageView, statement_upload, transaction_list

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('about/', AboutPageView.as_view(), name='about'),
    path('upload_csv/', statement_upload, name='upload_csv'),
    path('list_transactions/', transaction_list, name='transaction_list')
]