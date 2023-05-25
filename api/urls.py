# api/urls.py
from django.urls import path
from .views import ExpenseAPIView
from .views import RevenueAPIView

urlpatterns = [
    path('expense', ExpenseAPIView.as_view()),
    path('revenue', RevenueAPIView.as_view()),
    #path('expense/<int:pk>/edit', ExpenseUpdateDemoView.as_view(), name='expense_edit_demo'),
]