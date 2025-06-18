# api/views.py
import os
import uuid
from django.http import HttpResponse
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

# Import from your existing pdf_app
from pdf_app.watermark.service import PDFWatermarkService
from pdf_app.utils import add_qr_code_to_pdf, encode_message_in_pdf_font_stego

from .serializers import (
    WatermarkSerializer,
    QRCodeSerializer,
    FontSteganographySerializer,
    CombinedSteganographySerializer,
    SelectedSteganographySerializer,
)


def create_temp_file(pdf_file, prefix="temp_"):
    """Helper function to create temporary files"""
    temp_dir = getattr(settings, "MEDIA_ROOT", "/tmp")
    os.makedirs(temp_dir, exist_ok=True)

    temp_filename = f"{prefix}{uuid.uuid4().hex}.pdf"
    temp_path = os.path.join(temp_dir, temp_filename)

    with open(temp_path, "wb+") as destination:
        for chunk in pdf_file.chunks():
            destination.write(chunk)

    return temp_path


def cleanup_temp_file(file_path):
    """Helper function to clean up temporary files"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up temp file {file_path}: {e}")


@api_view(["GET"])
def api_info(request):
    """API endpoint to get information about available steganography methods"""
    return Response(
        {
            "api_version": "1.0",
            "message": "PDF Steganography REST API",
            "available_endpoints": {
                "info": {
                    "url": "/api/",
                    "method": "GET",
                    "description": "Get API information",
                },
                "watermark": {
                    "url": "/api/watermark/",
                    "method": "POST",
                    "description": "Add invisible watermark to PDF",
                    "required_fields": ["pdf_file", "watermark_text"],
                    "optional_fields": ["watermark_text"],
                },
                "qr_code": {
                    "url": "/api/qr-code/",
                    "method": "POST",
                    "description": "Add QR code with encoded email to PDF",
                    "required_fields": ["pdf_file", "email"],
                },
                "font_steganography": {
                    "url": "/api/font-steganography/",
                    "method": "POST",
                    "description": "Hide message using font size variations",
                    "required_fields": ["pdf_file", "secret_message", "cover_text"],
                },
                "all_methods": {
                    "url": "/api/all/",
                    "method": "POST",
                    "description": "Apply all steganography methods",
                    "required_fields": ["pdf_file"],
                    "note": "Enable specific methods using enable_* flags",
                },
                "selected_methods": {
                    "url": "/api/selected/",
                    "method": "POST",
                    "description": "Apply selected steganography methods",
                    "required_fields": ["pdf_file", "methods"],
                    "note": "Provide additional fields based on selected methods",
                },
            },
        }
    )


@api_view(["POST"])

@parser_classes([MultiPartParser, FormParser])
def add_watermark_api(request):
    """API endpoint to add invisible watermark to PDF"""
    serializer = WatermarkSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    pdf_file = serializer.validated_data["pdf_file"]
    watermark_text = serializer.validated_data["watermark_text"]

    try:
        # Add watermark using existing service
        watermarked_pdf = PDFWatermarkService.add_invisible_watermark(
            pdf_file, watermark_text, PDFWatermarkService.WATERMARK_COLOR
        )

        # Create response
        response = HttpResponse(
            watermarked_pdf.getvalue(), content_type="application/pdf"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="watermarked_{pdf_file.name}"'
        )

        return response

    except Exception as e:
        return Response(
            {"error": f"Error adding watermark: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])

@parser_classes([MultiPartParser, FormParser])
def add_qr_code_api(request):
    """API endpoint to add QR code to PDF"""
    serializer = QRCodeSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    pdf_file = serializer.validated_data["pdf_file"]
    email = serializer.validated_data["email"]

    temp_input_path = None
    temp_output_path = None

    try:
        # Create temporary files
        temp_input_path = create_temp_file(pdf_file, "qr_input_")
        temp_output_path = os.path.join(
            os.path.dirname(temp_input_path), f"qr_output_{uuid.uuid4().hex}.pdf"
        )

        # Add QR code
        add_qr_code_to_pdf(temp_input_path, temp_output_path, email)

        # Create response
        with open(temp_output_path, "rb") as pdf_file_result:
            response = HttpResponse(
                pdf_file_result.read(), content_type="application/pdf"
            )
            response["Content-Disposition"] = (
                f'attachment; filename="qr_code_{pdf_file.name}"'
            )
            return response

    except Exception as e:
        return Response(
            {"error": f"Error adding QR code: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        # Cleanup
        cleanup_temp_file(temp_input_path)
        cleanup_temp_file(temp_output_path)


@api_view(["POST"])

@parser_classes([MultiPartParser, FormParser])
def add_font_steganography_api(request):
    """API endpoint to add font steganography to PDF"""
    serializer = FontSteganographySerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    pdf_file = serializer.validated_data["pdf_file"]
    secret_message = serializer.validated_data["secret_message"]
    cover_text = serializer.validated_data["cover_text"]

    temp_input_path = None
    temp_output_path = None

    try:
        # Create temporary files
        temp_input_path = create_temp_file(pdf_file, "font_input_")
        temp_output_path = os.path.join(
            os.path.dirname(temp_input_path), f"font_output_{uuid.uuid4().hex}.pdf"
        )

        # Add font steganography
        result = encode_message_in_pdf_font_stego(
            temp_input_path, temp_output_path, secret_message, cover_text
        )

        if not result["success"]:
            return Response(
                {"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create response
        with open(temp_output_path, "rb") as pdf_file_result:
            response = HttpResponse(
                pdf_file_result.read(), content_type="application/pdf"
            )
            response["Content-Disposition"] = (
                f'attachment; filename="font_stego_{pdf_file.name}"'
            )
            return response

    except Exception as e:
        return Response(
            {"error": f"Error adding font steganography: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        # Cleanup
        cleanup_temp_file(temp_input_path)
        cleanup_temp_file(temp_output_path)


@api_view(["POST"])

@parser_classes([MultiPartParser, FormParser])
def add_all_steganography_api(request):
    """API endpoint to apply all three steganography methods"""
    serializer = CombinedSteganographySerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    pdf_file = serializer.validated_data["pdf_file"]

    # Get method flags
    enable_watermark = serializer.validated_data.get("enable_watermark", False)
    enable_qr_code = serializer.validated_data.get("enable_qr_code", False)
    enable_font_stego = serializer.validated_data.get("enable_font_stego", False)

    # Get method parameters
    watermark_text = serializer.validated_data.get("watermark_text")
    email = serializer.validated_data.get("email")
    secret_message = serializer.validated_data.get("secret_message")
    cover_text = serializer.validated_data.get("cover_text")

    temp_files = []

    try:
        current_pdf = pdf_file
        methods_applied = []

        # Step 1: Add watermark if enabled
        if enable_watermark and watermark_text:
            watermarked_pdf = PDFWatermarkService.add_invisible_watermark(
                current_pdf, watermark_text, PDFWatermarkService.WATERMARK_COLOR
            )

            # Save to temp file for next step
            temp_path = os.path.join(
                getattr(settings, "MEDIA_ROOT", "/tmp"), f"step1_{uuid.uuid4().hex}.pdf"
            )
            with open(temp_path, "wb") as f:
                f.write(watermarked_pdf.getvalue())

            temp_files.append(temp_path)

            if hasattr(current_pdf, "close") and current_pdf != pdf_file:
                current_pdf.close()
            current_pdf = open(temp_path, "rb")
            methods_applied.append("watermark")

        # Step 2: Add QR code if enabled
        if enable_qr_code and email:
            temp_input_path = create_temp_file(current_pdf, "qr_step_")
            temp_output_path = os.path.join(
                os.path.dirname(temp_input_path),
                f"qr_step_output_{uuid.uuid4().hex}.pdf",
            )

            add_qr_code_to_pdf(temp_input_path, temp_output_path, email)

            temp_files.extend([temp_input_path, temp_output_path])

            if hasattr(current_pdf, "close") and current_pdf != pdf_file:
                current_pdf.close()
            current_pdf = open(temp_output_path, "rb")
            methods_applied.append("qr_code")

        # Step 3: Add font steganography if enabled
        if enable_font_stego and secret_message and cover_text:
            temp_input_path = create_temp_file(current_pdf, "font_step_")
            temp_output_path = os.path.join(
                os.path.dirname(temp_input_path),
                f"font_step_output_{uuid.uuid4().hex}.pdf",
            )

            result = encode_message_in_pdf_font_stego(
                temp_input_path, temp_output_path, secret_message, cover_text
            )

            if not result["success"]:
                return Response(
                    {"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST
                )

            temp_files.extend([temp_input_path, temp_output_path])

            if hasattr(current_pdf, "close") and current_pdf != pdf_file:
                current_pdf.close()
            current_pdf = open(temp_output_path, "rb")
            methods_applied.append("font_stego")

        # Create final response
        final_pdf_content = current_pdf.read()
        if hasattr(current_pdf, "close") and current_pdf != pdf_file:
            current_pdf.close()

        response = HttpResponse(final_pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="all_stego_{pdf_file.name}"'
        )
        response["X-Methods-Applied"] = ",".join(methods_applied)

        return response

    except Exception as e:
        return Response(
            {"error": f"Error applying steganography methods: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        # Cleanup all temp files
        for temp_file in temp_files:
            cleanup_temp_file(temp_file)


@api_view(["POST"])

@parser_classes([MultiPartParser, FormParser])
def add_selected_steganography_api(request):
    """API endpoint to apply selected steganography methods"""
    serializer = SelectedSteganographySerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    pdf_file = serializer.validated_data["pdf_file"]
    methods = serializer.validated_data["methods"]

    # Get method parameters
    watermark_text = serializer.validated_data.get("watermark_text")
    email = serializer.validated_data.get("email")
    secret_message = serializer.validated_data.get("secret_message")
    cover_text = serializer.validated_data.get("cover_text")

    temp_files = []

    try:
        current_pdf = pdf_file
        methods_applied = []

        # Apply methods in order
        for method in methods:
            if method == "watermark" and watermark_text:
                watermarked_pdf = PDFWatermarkService.add_invisible_watermark(
                    current_pdf, watermark_text, PDFWatermarkService.WATERMARK_COLOR
                )

                # Save to temp file for next step
                temp_path = os.path.join(
                    getattr(settings, "MEDIA_ROOT", "/tmp"),
                    f"watermark_{uuid.uuid4().hex}.pdf",
                )
                with open(temp_path, "wb") as f:
                    f.write(watermarked_pdf.getvalue())

                temp_files.append(temp_path)

                if hasattr(current_pdf, "close") and current_pdf != pdf_file:
                    current_pdf.close()
                current_pdf = open(temp_path, "rb")
                methods_applied.append("watermark")

            elif method == "qr_code" and email:
                temp_input_path = create_temp_file(current_pdf, "qr_selected_")
                temp_output_path = os.path.join(
                    os.path.dirname(temp_input_path),
                    f"qr_selected_output_{uuid.uuid4().hex}.pdf",
                )

                add_qr_code_to_pdf(temp_input_path, temp_output_path, email)

                temp_files.extend([temp_input_path, temp_output_path])

                if hasattr(current_pdf, "close") and current_pdf != pdf_file:
                    current_pdf.close()
                current_pdf = open(temp_output_path, "rb")
                methods_applied.append("qr_code")

            elif method == "font_stego" and secret_message and cover_text:
                temp_input_path = create_temp_file(current_pdf, "font_selected_")
                temp_output_path = os.path.join(
                    os.path.dirname(temp_input_path),
                    f"font_selected_output_{uuid.uuid4().hex}.pdf",
                )

                result = encode_message_in_pdf_font_stego(
                    temp_input_path, temp_output_path, secret_message, cover_text
                )

                if not result["success"]:
                    return Response(
                        {"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST
                    )

                temp_files.extend([temp_input_path, temp_output_path])

                if hasattr(current_pdf, "close") and current_pdf != pdf_file:
                    current_pdf.close()
                current_pdf = open(temp_output_path, "rb")
                methods_applied.append("font_stego")

        # Create final response
        final_pdf_content = current_pdf.read()
        if hasattr(current_pdf, "close") and current_pdf != pdf_file:
            current_pdf.close()

        response = HttpResponse(final_pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="selected_stego_{pdf_file.name}"'
        )
        response["X-Methods-Applied"] = ",".join(methods_applied)

        return response

    except Exception as e:
        return Response(
            {"error": f"Error applying selected steganography methods: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        # Cleanup all temp files
        for temp_file in temp_files:
            cleanup_temp_file(temp_file)
