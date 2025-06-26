# api/urls.py
from django.urls import path
from . import views

app_name = "api"

urlpatterns = [
    # API info endpoint
    path("", views.api_info, name="api_info"),
    # Individual steganography methods
    path("watermark/", views.add_watermark_api, name="add_watermark"),
    path("qr-code/", views.add_qr_code_api, name="add_qr_code"),
    path(
        "font-steganography/",
        views.add_font_steganography_api,
        name="add_font_steganography",
    ),
    # Combined methods
    path("all/", views.add_all_steganography_api, name="add_all_steganography"),
    path(
        "selected/",
        views.add_selected_steganography_api,
        name="add_selected_steganography",
    ),
]
