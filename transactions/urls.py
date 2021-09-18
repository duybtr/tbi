# transactions/urls.py
from django.urls import path
from .views import (
    HomePageView, 
    AboutPageView, 
    TransactionUpdateView, 
    TransactionDeleteView,
    TransactionListView,
    statement_upload, 
    #transaction_list, 
    CreateExpenseView,
    ExpenseListView,
    ExpenseUpdateView,
    ExpenseDeleteView,
    MatchListView,
    match_expense,
    remove_match
)

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('about/', AboutPageView.as_view(), name='about'),
    path('upload_csv/', statement_upload, name='upload_csv'),
    path('upload_invoice/', CreateExpenseView.as_view(), name='upload_invoice'),
    path('list_transactions/', TransactionListView.as_view(), name='transaction_list'),
    path('<int:pk>/transaction_edit/', TransactionUpdateView.as_view(), name='transaction_edit'),
    path('<int:pk>/expense_edit/', ExpenseUpdateView.as_view(), name='expense_edit'),
    path('<int:pk>/expense_delete/', ExpenseDeleteView.as_view(), name='expense_delete'),
    path('list_expenses/', ExpenseListView.as_view(), name='expense_list'),
    path('<int:pk>/list_matches/', MatchListView.as_view(), name='match_list'),
    path('<int:transaction_pk>/<int:expense_pk>/match_expense', match_expense, name='match_expense'),
    path('<int:transaction_pk>/remove_match', remove_match, name='remove_match'),
    path('<int:pk>/transaction_delete', TransactionDeleteView.as_view(), name='transaction_delete'),
]