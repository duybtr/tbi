# transactions/urls.py
from django.urls import path
from .views import (
    HomePageView, 
    AboutPageView, 
    TransactionUpdateView, 
    statement_upload, 
    transaction_list, 
    CreateExpenseView,
    ExpenseListView,
    ExpenseUpdateView
)

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('about/', AboutPageView.as_view(), name='about'),
    path('upload_csv/', statement_upload, name='upload_csv'),
    path('upload_invoice/', CreateExpenseView.as_view(), name='upload_invoice'),
    path('list_transactions/', transaction_list, name='transaction_list'),
    path('<int:pk>/transaction_edit/', TransactionUpdateView.as_view(), name='transaction_edit'),
    path('<int:pk>/expense_edit/', ExpenseUpdateView.as_view(), name='expense_edit'),
    path('list_expenses/', ExpenseListView.as_view(), name='expense_list'),
]