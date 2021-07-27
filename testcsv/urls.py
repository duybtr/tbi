from django.urls import path
from .views import profile_upload

urlpatterns = [
    path('upload_csv/', profile_upload, name="test_csv")
]