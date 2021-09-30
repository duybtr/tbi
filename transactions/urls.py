# transactions/urls.py
from django.urls import path
from .views import (
    HomePageView, 
    AboutPageView, 
    TransactionUpdateView, 
    TransactionDeleteView,
    TransactionListView,
    StatementCreateView,
    StatementListView, 
    #transaction_list, 
    CreateExpenseView,
    ExpenseListView,
    ExpenseUpdateView,
    ExpenseDeleteView,
    CreateRevenueView,
    MatchingRevenueListView,
    RevenueListView,
    RevenueUpdateView,
    RevenueDeleteView,
    #MatchListView,
    MatchingExpenseListView,
    MatchingRevenueListView,
    match_expense,
    match_revenue,
    remove_match
)

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('about/', AboutPageView.as_view(), name='about'),
    path('upload_csv/', StatementCreateView.as_view(), name='upload_csv'),
    path('upload_invoice/', CreateExpenseView.as_view(), name='upload_invoice'),
    path('upload_check/', CreateRevenueView.as_view(), name='upload_check'),
    path('list_transactions/', TransactionListView.as_view(), name='transaction_list'),
    path('<int:pk>/transaction_edit/', TransactionUpdateView.as_view(), name='transaction_edit'),
    path('<int:pk>/expense_edit/', ExpenseUpdateView.as_view(), name='expense_edit'),
    path('<int:pk>/expense_delete/', ExpenseDeleteView.as_view(), name='expense_delete'),
    path('list_expenses/', ExpenseListView.as_view(), name='expense_list'),
    path('list_revenues/', RevenueListView.as_view(), name='revenue_list'),
    path('<int:pk>/revenue_edit', RevenueUpdateView.as_view(),name='revenue_edit'),
    path('<int:pk>/revenue_delete/', RevenueDeleteView.as_view(), name='revenue_delete'),
    path('<int:pk>/list_matching_revenues/', MatchingRevenueListView.as_view(), name='matching_revenue_list'),
    path('<int:pk>/list_matching_expenses/', MatchingExpenseListView.as_view(), name='matching_expense_list'),
    path('list_statements/', StatementListView.as_view(), name='statement_list'),
    #path('<int:pk>/list_matches/', MatchListView.as_view(), name='match_list'),
    path('<int:transaction_pk>/<int:expense_pk>/match_expense', match_expense, name='match_expense'),
    path('<int:transaction_pk>/remove_match', remove_match, name='remove_match'),
    path('<int:transaction_pk>/<int:revenue_pk>/match_revenue', match_revenue, name='match_revenue'),
    path('<int:transaction_pk>/remove_match', remove_match, name='remove_match'),
    path('<int:pk>/transaction_delete', TransactionDeleteView.as_view(), name='transaction_delete'),
]