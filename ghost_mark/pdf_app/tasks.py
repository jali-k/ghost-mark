# pdf_app/tasks.py
import os
import uuid
import time
from io import BytesIO
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.core.files.storage import default_storage

from .models import PDFProcessingJob
from .watermark.service import PDFWatermarkService
from .utils import add_qr_code_to_pdf, encode_message_in_pdf_font_stego


def create_temp_file_from_content(file_content, prefix="temp_"):
    """Helper function to create temporary files from file content"""
    temp_dir = getattr(settings, "MEDIA_ROOT", "/tmp")
    os.makedirs(temp_dir, exist_ok=True)

    temp_filename = f"{prefix}{uuid.uuid4().hex}.pdf"
    temp_path = os.path.join(temp_dir, temp_filename)

    with open(temp_path, "wb") as destination:
        destination.write(file_content)

    return temp_path


def cleanup_temp_file(file_path):
    """Helper function to clean up temporary files"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up temp file {file_path}: {e}")


@shared_task(bind=True)
def process_pdf_task(self, job_id):
    """
    Main task that processes PDF based on job configuration
    """
    try:
        # Get the job
        job = PDFProcessingJob.objects.get(job_id=job_id)

        # Update status and start time
        job.status = "PROCESSING"
        job.started_at = timezone.now()
        job.save()

        start_time = time.time()

        print(f"🚀 Starting job {job_id} - Type: {job.job_type}")

        # Read the input file
        if not job.input_file_path or not os.path.exists(job.input_file_path):
            raise Exception("Input file not found")

        with open(job.input_file_path, "rb") as f:
            current_pdf_content = f.read()

        temp_files = []  # Track temp files for cleanup

        # Process based on job type
        if job.job_type == "watermark":
            current_pdf_content = process_watermark(current_pdf_content, job)

        elif job.job_type == "qr_code":
            current_pdf_content = process_qr_code(current_pdf_content, job, temp_files)

        elif job.job_type == "font_stego":
            current_pdf_content = process_font_stego(
                current_pdf_content, job, temp_files
            )

        elif job.job_type == "all_methods":
            current_pdf_content = process_all_methods(
                current_pdf_content, job, temp_files
            )

        elif job.job_type == "selected_methods":
            current_pdf_content = process_selected_methods(
                current_pdf_content, job, temp_files
            )

        else:
            raise Exception(f"Unknown job type: {job.job_type}")

        # Save the output file
        output_filename = f"processed_{job_id}_{job.original_filename}"
        output_path = os.path.join(settings.MEDIA_ROOT, "processed", output_filename)

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(current_pdf_content)

        # Update job with completion info
        processing_time = time.time() - start_time
        job.status = "COMPLETED"
        job.completed_at = timezone.now()
        job.output_file_path = output_path
        job.processing_time = processing_time
        job.save()

        # Cleanup temp files
        for temp_file in temp_files:
            cleanup_temp_file(temp_file)

        print(f"✅ Job {job_id} completed in {processing_time:.2f} seconds")

        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "processing_time": processing_time,
            "output_path": output_path,
        }

    except Exception as e:
        print(f"❌ Job {job_id} failed: {str(e)}")

        # Update job with error info
        try:
            job = PDFProcessingJob.objects.get(job_id=job_id)
            job.status = "FAILED"
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
        except:
            pass

        # Re-raise the exception so Celery knows the task failed
        raise


def process_watermark(pdf_content, job):
    """Process watermark only"""
    pdf_buffer = BytesIO(pdf_content)
    watermarked_pdf = PDFWatermarkService.add_invisible_watermark(
        pdf_buffer, job.watermark_text, PDFWatermarkService.WATERMARK_COLOR
    )
    return watermarked_pdf.getvalue()


def process_qr_code(pdf_content, job, temp_files):
    """Process QR code only"""
    temp_input_path = create_temp_file_from_content(pdf_content, "qr_input_")
    temp_output_path = os.path.join(
        os.path.dirname(temp_input_path), f"qr_output_{uuid.uuid4().hex}.pdf"
    )

    temp_files.extend([temp_input_path, temp_output_path])

    add_qr_code_to_pdf(temp_input_path, temp_output_path, job.email)

    with open(temp_output_path, "rb") as f:
        return f.read()


def process_font_stego(pdf_content, job, temp_files):
    """Process font steganography only"""
    temp_input_path = create_temp_file_from_content(pdf_content, "font_input_")
    temp_output_path = os.path.join(
        os.path.dirname(temp_input_path), f"font_output_{uuid.uuid4().hex}.pdf"
    )

    temp_files.extend([temp_input_path, temp_output_path])

    result = encode_message_in_pdf_font_stego(
        temp_input_path, temp_output_path, job.secret_message, job.cover_text
    )

    if not result["success"]:
        raise Exception(result["error"])

    with open(temp_output_path, "rb") as f:
        return f.read()


def process_all_methods(pdf_content, job, temp_files):
    """Process all methods in sequence"""
    current_content = pdf_content

    # Step 1: Watermark (if enabled and has text)
    if job.watermark_text:
        print(f"  Adding watermark...")
        current_content = process_watermark(current_content, job)

    # Step 2: QR Code (if enabled and has email)
    if job.email:
        print(f"  Adding QR code...")
        current_content = process_qr_code(current_content, job, temp_files)

    # Step 3: Font Steganography (if enabled and has required params)
    if job.secret_message and job.cover_text:
        print(f"  Adding font steganography...")
        current_content = process_font_stego(current_content, job, temp_files)

    return current_content


def process_selected_methods(pdf_content, job, temp_files):
    """Process selected methods in order"""
    current_content = pdf_content
    methods = job.selected_methods.split(",") if job.selected_methods else []

    for method in methods:
        method = method.strip()

        if method == "watermark" and job.watermark_text:
            print(f"  Adding watermark...")
            current_content = process_watermark(current_content, job)

        elif method == "qr_code" and job.email:
            print(f"  Adding QR code...")
            current_content = process_qr_code(current_content, job, temp_files)

        elif method == "font_stego" and job.secret_message and job.cover_text:
            print(f"  Adding font steganography...")
            current_content = process_font_stego(current_content, job, temp_files)

    return current_content


@shared_task
def cleanup_expired_jobs():
    """
    Cleanup task to remove expired jobs and their files
    Run this periodically (e.g., every 15 minutes)
    """
    from django.utils import timezone
    from datetime import timedelta

    # Find jobs older than 15 minutes
    cutoff_time = timezone.now() - timedelta(minutes=15)
    expired_jobs = PDFProcessingJob.objects.filter(created_at__lt=cutoff_time)

    cleaned_count = 0
    for job in expired_jobs:
        try:
            # Clean up files
            job.cleanup_files()
            # Delete the job record
            job.delete()
            cleaned_count += 1
        except Exception as e:
            print(f"Error cleaning up job {job.job_id}: {e}")

    print(f"🧹 Cleaned up {cleaned_count} expired jobs")
    return f"Cleaned up {cleaned_count} expired jobs"
