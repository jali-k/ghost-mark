import os
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

# Create your models here.


class PDFProcessingJob(models.Model):
    JOB_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    JOB_TYPE_CHOICES = [
        ("watermark", "Watermark Only"),
        ("qr_code", "QR Code Only"),
        ("font_stego", "Font Steganography Only"),
        ("all_methods", "All Methods"),
        ("selected_methods", "Selected Methods"),
    ]

    # Job identification
    job_id = models.CharField(max_length=100, unique=True, db_index=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=JOB_STATUS_CHOICES, default="PENDING"
    )

    # Processing parameters (stored as JSON-like fields)
    original_filename = models.CharField(max_length=255)

    # Method-specific parameters
    watermark_text = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    secret_message = models.CharField(max_length=500, blank=True, null=True)
    cover_text = models.TextField(blank=True, null=True)

    # For selected methods
    selected_methods = models.CharField(
        max_length=100, blank=True, null=True
    )  # comma-separated

    # File paths
    input_file_path = models.CharField(max_length=500, blank=True, null=True)
    output_file_path = models.CharField(max_length=500, blank=True, null=True)

    # Processing info
    error_message = models.TextField(blank=True, null=True)
    processing_time = models.FloatField(null=True, blank=True)  # seconds

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Job {self.job_id} - {self.job_type} - {self.status}"

    def is_expired(self):
        """Check if job is older than 15 minutes"""
        expiry_time = self.created_at + timedelta(minutes=15)
        return timezone.now() > expiry_time

    def get_output_file_url(self):
        """Get URL for downloading the processed file"""
        if self.output_file_path and os.path.exists(self.output_file_path):
            # Return relative path from MEDIA_ROOT
            rel_path = os.path.relpath(self.output_file_path, settings.MEDIA_ROOT)
            return f"{settings.MEDIA_URL}{rel_path}"
        return None

    def cleanup_files(self):
        """Clean up input and output files"""
        for file_path in [self.input_file_path, self.output_file_path]:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error removing file {file_path}: {e}")


class WatermarkedDocument(models.Model):
    document = models.FileField(upload_to="documents/")
    watermarked_document = models.FileField(
        upload_to="watermarked_documents/", null=True, blank=True
    )
    watermark_text = models.CharField(max_length=255)
    watermark_color = models.CharField(max_length=7, default="#fffffe")
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document {self.id} - {self.watermark_text}"
