# api/views_async.py
import os
import uuid
from django.http import HttpResponse, Http404
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from pdf_app.models import PDFProcessingJob
from pdf_app.tasks import process_pdf_task
from .serializers import (
    WatermarkSerializer,
    QRCodeSerializer,
    FontSteganographySerializer,
    CombinedSteganographySerializer,
    SelectedSteganographySerializer,
)


def save_uploaded_file(uploaded_file, job_id):
    """Save uploaded file to temp location and return path"""
    temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)

    temp_filename = f"{job_id}_{uploaded_file.name}"
    temp_path = os.path.join(temp_dir, temp_filename)

    with open(temp_path, "wb+") as destination:
        if hasattr(uploaded_file, "chunks"):
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        else:
            uploaded_file.seek(0)
            destination.write(uploaded_file.read())

    return temp_path


def create_job_response(job):
    """Create standardized job response"""
    return Response(
        {
            "job_id": job.job_id,
            "status": job.status,
            "job_type": job.job_type,
            "created_at": job.created_at.isoformat(),
            "message": "Job created successfully. Use the job_id to check status.",
            "status_url": f"/api/status/{job.job_id}/",
            "download_url": (
                f"/api/download/{job.job_id}/" if job.status == "COMPLETED" else None
            ),
        },
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def add_watermark_async(request):
    """Async API endpoint to add invisible watermark to PDF"""
    serializer = WatermarkSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Save uploaded file
        pdf_file = serializer.validated_data["pdf_file"]
        input_file_path = save_uploaded_file(pdf_file, job_id)

        # Create job record
        job = PDFProcessingJob.objects.create(
            job_id=job_id,
            job_type="watermark",
            original_filename=pdf_file.name,
            watermark_text=serializer.validated_data["watermark_text"],
            input_file_path=input_file_path,
        )

        # Queue the task
        process_pdf_task.delay(job_id)

        return create_job_response(job)

    except Exception as e:
        return Response(
            {"error": f"Error creating job: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def add_qr_code_async(request):
    """Async API endpoint to add QR code to PDF"""
    serializer = QRCodeSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        job_id = str(uuid.uuid4())
        pdf_file = serializer.validated_data["pdf_file"]
        input_file_path = save_uploaded_file(pdf_file, job_id)

        job = PDFProcessingJob.objects.create(
            job_id=job_id,
            job_type="qr_code",
            original_filename=pdf_file.name,
            email=serializer.validated_data["email"],
            input_file_path=input_file_path,
        )

        process_pdf_task.delay(job_id)

        return create_job_response(job)

    except Exception as e:
        return Response(
            {"error": f"Error creating job: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def add_font_steganography_async(request):
    """Async API endpoint to add font steganography to PDF"""
    serializer = FontSteganographySerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        job_id = str(uuid.uuid4())
        pdf_file = serializer.validated_data["pdf_file"]
        input_file_path = save_uploaded_file(pdf_file, job_id)

        job = PDFProcessingJob.objects.create(
            job_id=job_id,
            job_type="font_stego",
            original_filename=pdf_file.name,
            secret_message=serializer.validated_data["secret_message"],
            cover_text=serializer.validated_data["cover_text"],
            input_file_path=input_file_path,
        )

        process_pdf_task.delay(job_id)

        return create_job_response(job)

    except Exception as e:
        return Response(
            {"error": f"Error creating job: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def add_all_steganography_async(request):
    """Async API endpoint to apply all steganography methods"""
    serializer = CombinedSteganographySerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        job_id = str(uuid.uuid4())
        pdf_file = serializer.validated_data["pdf_file"]
        input_file_path = save_uploaded_file(pdf_file, job_id)

        job = PDFProcessingJob.objects.create(
            job_id=job_id,
            job_type="all_methods",
            original_filename=pdf_file.name,
            watermark_text=serializer.validated_data.get("watermark_text"),
            email=serializer.validated_data.get("email"),
            secret_message=serializer.validated_data.get("secret_message"),
            cover_text=serializer.validated_data.get("cover_text"),
            input_file_path=input_file_path,
        )

        process_pdf_task.delay(job_id)

        return create_job_response(job)

    except Exception as e:
        return Response(
            {"error": f"Error creating job: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def add_selected_steganography_async(request):
    """Async API endpoint to apply selected steganography methods"""
    serializer = SelectedSteganographySerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        job_id = str(uuid.uuid4())
        pdf_file = serializer.validated_data["pdf_file"]
        input_file_path = save_uploaded_file(pdf_file, job_id)

        methods = serializer.validated_data["methods"]

        job = PDFProcessingJob.objects.create(
            job_id=job_id,
            job_type="selected_methods",
            original_filename=pdf_file.name,
            selected_methods=",".join(methods),
            watermark_text=serializer.validated_data.get("watermark_text"),
            email=serializer.validated_data.get("email"),
            secret_message=serializer.validated_data.get("secret_message"),
            cover_text=serializer.validated_data.get("cover_text"),
            input_file_path=input_file_path,
        )

        process_pdf_task.delay(job_id)

        return create_job_response(job)

    except Exception as e:
        return Response(
            {"error": f"Error creating job: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def job_status(request, job_id):
    """Get job status and details"""
    try:
        job = PDFProcessingJob.objects.get(job_id=job_id)

        response_data = {
            "job_id": job.job_id,
            "status": job.status,
            "job_type": job.job_type,
            "original_filename": job.original_filename,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "processing_time": job.processing_time,
            "error_message": job.error_message,
            "download_url": (
                f"/api/download/{job.job_id}/" if job.status == "COMPLETED" else None
            ),
        }

        return Response(response_data)

    except PDFProcessingJob.DoesNotExist:
        return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
def download_processed_pdf(request, job_id):
    """Download processed PDF file"""
    try:
        job = PDFProcessingJob.objects.get(job_id=job_id)

        if job.status != "COMPLETED":
            return Response(
                {"error": f"Job not completed. Current status: {job.status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not job.output_file_path or not os.path.exists(job.output_file_path):
            return Response(
                {"error": "Processed file not found or expired"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Read and return the file
        with open(job.output_file_path, "rb") as f:
            response = HttpResponse(f.read(), content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="{job.original_filename}"'
            )
            return response

    except PDFProcessingJob.DoesNotExist:
        return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
def job_list(request):
    """Get list of recent jobs (for debugging/admin)"""
    jobs = PDFProcessingJob.objects.all()[:50]  # Last 50 jobs

    job_data = []
    for job in jobs:
        job_data.append(
            {
                "job_id": job.job_id,
                "status": job.status,
                "job_type": job.job_type,
                "original_filename": job.original_filename,
                "created_at": job.created_at.isoformat(),
                "processing_time": job.processing_time,
            }
        )

    return Response({"jobs": job_data, "total_count": len(job_data)})
