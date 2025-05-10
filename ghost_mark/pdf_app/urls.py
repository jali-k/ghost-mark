from django.urls import path
from . import views

app_name = "pdf_app"

urlpatterns = [
    path("", views.index, name="index"),
    path("recover/", views.recover_email, name="recover_email"),
]
