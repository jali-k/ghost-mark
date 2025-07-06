# api/urls.py
from django.urls import path
from . import views, views_async

app_name = "api"

urlpatterns = [
    # API info endpoint
    path("", views.api_info, name="api_info"),
    # ===================
    # ASYNC ENDPOINTS (NEW) - Recommended for production
    # ===================
    # Individual steganography methods (async)
    path(
        "async/watermark/", views_async.add_watermark_async, name="add_watermark_async"
    ),
    path("async/qr-code/", views_async.add_qr_code_async, name="add_qr_code_async"),
    path(
        "async/font-steganography/",
        views_async.add_font_steganography_async,
        name="add_font_steganography_async",
    ),
    # Combined methods (async)
    path(
        "async/all/",
        views_async.add_all_steganography_async,
        name="add_all_steganography_async",
    ),
    path(
        "async/selected/",
        views_async.add_selected_steganography_async,
        name="add_selected_steganography_async",
    ),
    # Job management endpoints
    path("status/<str:job_id>/", views_async.job_status, name="job_status"),
    path(
        "download/<str:job_id>/",
        views_async.download_processed_pdf,
        name="download_processed_pdf",
    ),
    path("jobs/", views_async.job_list, name="job_list"),  # For debugging/admin
    
    # ===================
    # LEGACY ENDPOINTS (BLOCKING) - Keep for backward compatibility
    # ===================
    
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
