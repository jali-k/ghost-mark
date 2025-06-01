import os
import uuid
import cv2
import numpy as np
from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views import View
from django.conf import settings
from django.core.files.base import ContentFile
from io import BytesIO
from .forms import (
    PDFEmailForm,
    PDFQRCodeForm,
    QRCodeScanForm,
    WatermarkForm,
    ExtractWatermarkForm,
    FontStegoEncodeForm,
    FontStegoDecodeForm,
)
from .utils import (
    email_to_number,
    number_to_email,
    add_border_to_pdf,
    add_qr_code_to_pdf,
    generate_qr_code,
    process_qr_code,
    encode_message_in_pdf_font_stego,
    decode_message_from_pdf_font_stego,
)

# Import the watermark service
from .watermark.service import PDFWatermarkService
from .models import WatermarkedDocument


def index(request):
    """Homepage view - displays feature cards and info."""
    return render(request, "pdf_app/index.html")


def add_border(request):
    """View for adding email tracking borders to PDFs."""
    if request.method == "POST":
        form = PDFEmailForm(request.POST, request.FILES)
        if form.is_valid():
            # Get the uploaded PDF and email
            pdf_file = request.FILES["pdf_file"]
            email = form.cleaned_data["email"]

            # Convert email to a 10-digit number
            email_number, _ = email_to_number(email)
            print(f"Email converted to number: {email_number}")

            # Create a unique filename for the output PDF
            output_filename = f"border_{uuid.uuid4().hex}.pdf"
            output_path = os.path.join(settings.MEDIA_ROOT, output_filename)

            # Save the uploaded PDF temporarily
            temp_pdf_path = os.path.join(
                settings.MEDIA_ROOT, f"temp_{uuid.uuid4().hex}.pdf"
            )
            with open(temp_pdf_path, "wb+") as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)

            # Process the PDF, adding borders
            add_border_to_pdf(temp_pdf_path, output_path, email_number)

            # Clean up the temporary file
            os.unlink(temp_pdf_path)

            # Return the processed PDF as a download
            return FileResponse(
                open(output_path, "rb"),
                as_attachment=True,
                filename=f"bordered_{pdf_file.name}",
            )
    else:
        form = PDFEmailForm()

    return render(request, "pdf_app/add_border.html", {"form": form})


def recover_email(request):
    """
    View to demonstrate the email recovery from the 10-digit number.
    In a real application, you'd need a way to extract the number from the PDF.
    """
    if request.method == "POST":
        # Extract the number from request
        number = request.POST.get("number", "")

        if number and len(number) == 20 and number.isdigit():
            # Recover the email
            email = number_to_email(number)
            return HttpResponse(f"The recovered email is: {email}")
        else:
            return HttpResponse("Please provide a valid 10-digit number.", status=400)

    # Simple form for demonstration
    return render(request, "pdf_app/recover.html")


# Add the new watermark views
class WatermarkPDFView(View):
    """View for adding invisible watermarks to PDFs."""

    template_name = "pdf_app/watermark.html"

    def get(self, request):
        """Display the watermark form."""
        form = WatermarkForm()
        context = {"form": form, "fixed_color": PDFWatermarkService.WATERMARK_COLOR}
        return render(request, self.template_name, context)

    def post(self, request):
        """Process the form and add watermark to PDF."""
        # Get our fixed color
        fixed_color = PDFWatermarkService.WATERMARK_COLOR

        # Add the watermark color to POST data to ensure it's always present
        post_data = request.POST.copy()
        post_data["watermark_color"] = fixed_color

        form = WatermarkForm(post_data, request.FILES)
        if not form.is_valid():
            return render(
                request, self.template_name, {"form": form, "fixed_color": fixed_color}
            )

        # Get form data
        pdf_file = request.FILES["document"]
        watermark_text = form.cleaned_data.get("watermark_text") or str(uuid.uuid4())

        # Create and save the document instance
        doc = form.save(commit=False)
        doc.watermark_text = watermark_text
        doc.watermark_color = fixed_color  # Use our fixed color
        doc.save()

        # Add watermark
        watermarked_pdf = PDFWatermarkService.add_invisible_watermark(
            pdf_file, watermark_text, fixed_color  # Pass our fixed color
        )

        # Save the watermarked file
        filename = f"watermarked_{os.path.basename(pdf_file.name)}"
        doc.watermarked_document.save(filename, ContentFile(watermarked_pdf.getvalue()))

        # Handle AJAX requests
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": True,
                    "download_url": doc.watermarked_document.url,
                    "document_id": doc.id,
                }
            )

        # For regular form submissions
        return redirect("pdf_app:download_watermarked", doc_id=doc.id)


class DownloadWatermarkedView(View):
    """View for downloading watermarked PDFs."""

    def get(self, request, doc_id):
        """Download the watermarked PDF."""
        try:
            doc = WatermarkedDocument.objects.get(id=doc_id)
            response = HttpResponse(
                doc.watermarked_document, content_type="application/pdf"
            )
            response["Content-Disposition"] = (
                f'attachment; filename="{os.path.basename(doc.watermarked_document.name)}"'
            )
            return response
        except WatermarkedDocument.DoesNotExist:
            return HttpResponse("Document not found", status=404)


class ExtractWatermarkView(View):
    """View for extracting watermarks from PDFs or images."""

    template_name = "pdf_app/extract_watermark.html"

    def get(self, request):
        """Display the extract watermark form."""
        form = ExtractWatermarkForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        """Process the form and extract watermark."""
        form = ExtractWatermarkForm(request.POST, request.FILES)
        if not form.is_valid():
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "Invalid form data"})
            return render(request, self.template_name, {"form": form})

        file = request.FILES["file"]

        # Save the file temporarily with a unique name to avoid conflicts
        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Use a unique filename to avoid conflicts
        import uuid

        unique_filename = f"{uuid.uuid4().hex}_{file.name}"
        temp_path = os.path.join(temp_dir, unique_filename)

        try:
            # Save the uploaded file
            with open(temp_path, "wb+") as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            # Extract the watermark
            watermark_text = PDFWatermarkService.extract_watermark(temp_path)

            # Clean up the temporary file
            os.remove(temp_path)

            # Handle AJAX requests
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True, "watermark_text": watermark_text})

            # For regular form submissions
            return render(
                request,
                self.template_name,
                {"form": form, "watermark_text": watermark_text},
            )

        except Exception as e:
            # Clean up in case of error
            if os.path.exists(temp_path):
                os.remove(temp_path)

            error_message = str(e)
            print(f"Error extracting watermark: {error_message}")  # Log for debugging

            # Handle AJAX requests - use consistent response format
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": error_message})

            # For regular form submissions
            return render(
                request, self.template_name, {"form": form, "error": error_message}
            )


def add_qr_code(request):
    """View for adding QR codes with encoded emails to PDFs."""
    if request.method == "POST":
        form = PDFQRCodeForm(request.POST, request.FILES)
        if form.is_valid():
            # Get the uploaded PDF and email
            pdf_file = request.FILES["pdf_file"]
            email = form.cleaned_data["email"]

            # Create a unique filename for the output PDF
            output_filename = f"qrcode_{uuid.uuid4().hex}.pdf"
            output_path = os.path.join(settings.MEDIA_ROOT, output_filename)

            # Save the uploaded PDF temporarily
            temp_pdf_path = os.path.join(
                settings.MEDIA_ROOT, f"temp_{uuid.uuid4().hex}.pdf"
            )
            with open(temp_pdf_path, "wb+") as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)

            try:
                # Process the PDF, adding QR code using our cipher approach
                add_qr_code_to_pdf(temp_pdf_path, output_path, email)

                # Clean up the temporary file
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)

                # Return the processed PDF as a download
                return FileResponse(
                    open(output_path, "rb"),
                    as_attachment=True,
                    filename=f"qrcode_{pdf_file.name}",
                )
            except Exception as e:
                # Clean up in case of error
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)

                # Log the error
                print(f"Error adding QR code: {str(e)}")

                # Return error response
                return HttpResponse(f"Error adding QR code: {str(e)}", status=500)
    else:
        form = PDFQRCodeForm()

    return render(request, "pdf_app/add_qr_code.html", {"form": form})


def scan_qr_code(request):
    """View for scanning QR codes and recovering emails."""
    result = None
    error = None

    if request.method == "POST":
        form = QRCodeScanForm(request.POST, request.FILES)
        if form.is_valid():
            # Get form data
            qr_code_image = form.cleaned_data.get("qr_code")
            code_string = form.cleaned_data.get("code_string")

            try:
                # If QR code image is uploaded
                if qr_code_image:
                    # Save the image temporarily
                    temp_dir = os.path.join(settings.MEDIA_ROOT, "temp")
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_path = os.path.join(temp_dir, qr_code_image.name)

                    with open(temp_path, "wb+") as destination:
                        for chunk in qr_code_image.chunks():
                            destination.write(chunk)

                    try:
                        # Read the QR code using OpenCV
                        import cv2

                        # Read the image
                        image = cv2.imread(temp_path)

                        if image is None:
                            error = "Failed to read the uploaded image."
                        else:
                            # Initialize QR code detector
                            detector = cv2.QRCodeDetector()
                            # Decode the QR code
                            data, bbox, _ = detector.detectAndDecode(image)

                            if data:
                                code_string = data
                            else:
                                error = "Could not detect a QR code in the image."
                    except Exception as e:
                        error = f"Error processing QR code image: {str(e)}"
                    finally:
                        # Clean up the temporary file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                # If we have a code string (either entered manually or from QR code)
                if code_string:
                    try:
                        # Process the QR code data using our cipher approach
                        result = process_qr_code(code_string)
                    except ValueError as e:
                        error = str(e)

            except Exception as e:
                error = f"Error processing QR code: {str(e)}"

        else:
            # Form validation failed
            error = "Please either upload a QR code image or enter the code manually."
    else:
        form = QRCodeScanForm()

    # For regular form submissions
    context = {"form": form, "result": result, "error": error}

    return render(request, "pdf_app/scan_qr_code.html", context)


def font_stego_encode(request):
    """View for encoding messages using font steganography."""
    if request.method == "POST":
        form = FontStegoEncodeForm(request.POST, request.FILES)
        if form.is_valid():
            # Get the uploaded PDF and form data
            pdf_file = request.FILES["pdf_file"]
            secret_message = form.cleaned_data["secret_message"]
            cover_text = form.cleaned_data["cover_text"]

            # Create a unique filename for the output PDF
            output_filename = f"font_stego_{uuid.uuid4().hex}.pdf"
            output_path = os.path.join(settings.MEDIA_ROOT, output_filename)

            # Save the uploaded PDF temporarily
            temp_pdf_path = os.path.join(
                settings.MEDIA_ROOT, f"temp_{uuid.uuid4().hex}.pdf"
            )
            with open(temp_pdf_path, "wb+") as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)

            try:
                # Process the PDF using font steganography
                result = encode_message_in_pdf_font_stego(
                    temp_pdf_path, output_path, secret_message, cover_text
                )

                # Clean up the temporary file
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)

                if result["success"]:
                    # Return the processed PDF as a download
                    return FileResponse(
                        open(output_path, "rb"),
                        as_attachment=True,
                        filename=f"font_stego_{pdf_file.name}",
                    )
                else:
                    # Return error if encoding failed
                    return render(
                        request,
                        "pdf_app/font_stego_encode.html",
                        {"form": form, "error": result["error"]},
                    )

            except Exception as e:
                # Clean up in case of error
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)

                # Log the error
                print(f"Error in font steganography encoding: {str(e)}")

                # Return error response
                return render(
                    request,
                    "pdf_app/font_stego_encode.html",
                    {"form": form, "error": f"Error encoding message: {str(e)}"},
                )
    else:
        form = FontStegoEncodeForm()

    return render(request, "pdf_app/font_stego_encode.html", {"form": form})


def font_stego_decode(request):
    """View for decoding messages from font steganography."""
    page_messages = None  # CHANGED: Now handles multiple pages
    binary_data = None
    error = None
    total_pages = None  # NEW: Track total pages

    if request.method == "POST":
        form = FontStegoDecodeForm(request.POST, request.FILES)
        if form.is_valid():
            # Get the uploaded PDF
            pdf_file = request.FILES["pdf_file"]

            # Save the uploaded PDF temporarily
            temp_pdf_path = os.path.join(
                settings.MEDIA_ROOT, f"temp_{uuid.uuid4().hex}.pdf"
            )
            with open(temp_pdf_path, "wb+") as destination:
                for chunk in pdf_file.chunks():
                    destination.write(chunk)

            try:
                # Decode the message from the PDF
                result = decode_message_from_pdf_font_stego(temp_pdf_path)

                # Clean up the temporary file
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)

                if result["success"]:
                    page_messages = result[
                        "page_messages"
                    ]  # CHANGED: Get page messages
                    binary_data = result["binary_data"]
                    total_pages = result["total_pages"]  # NEW: Get total pages
                else:
                    error = result["error"]

            except Exception as e:
                # Clean up in case of error
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)

                # Log the error
                print(f"Error in font steganography decoding: {str(e)}")
                error = f"Error decoding message: {str(e)}"

        else:
            error = "Please provide a valid PDF file."
    else:
        form = FontStegoDecodeForm()

    context = {
        "form": form,
        "page_messages": page_messages,  # CHANGED: Pass page messages
        "binary_data": binary_data,
        "error": error,
        "total_pages": total_pages,  # NEW: Pass total pages
    }

    return render(request, "pdf_app/font_stego_decode.html", context)
