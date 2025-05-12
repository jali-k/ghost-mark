from django.urls import path
from . import views

app_name = "pdf_app"

urlpatterns = [
    path("", views.index, name="index"),
    path("add-border/", views.add_border, name="add_border"),
    path("recover/", views.recover_email, name="recover_email"),
    path("watermark/", views.WatermarkPDFView.as_view(), name="watermark_pdf"),
    path(
        "watermark/download/<int:doc_id>/",
        views.DownloadWatermarkedView.as_view(),
        name="download_watermarked",
    ),
    path(
        "watermark/extract/",
        views.ExtractWatermarkView.as_view(),
        name="extract_watermark",
    ),
    # New QR code routes
    path("add-qr-code/", views.add_qr_code, name="add_qr_code"),
    path("scan-qr-code/", views.scan_qr_code, name="scan_qr_code"),
]
