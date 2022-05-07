# api/views.py
from rest_framework import generics
from transactions.models import Expense, Revenue
from .serializers import ExpenseSerializer, RevenueSerializer

# Create your views here.

class ExpenseAPIView(generics.ListAPIView):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

class RevenueAPIView(generics.ListAPIView):
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer