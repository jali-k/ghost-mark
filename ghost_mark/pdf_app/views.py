import os
import uuid
from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views import View
from django.conf import settings
from django.core.files.base import ContentFile
from io import BytesIO
from .forms import PDFEmailForm
from .utils import email_to_number, number_to_email, add_border_to_pdf

# Import the watermark service
from .watermark.service import PDFWatermarkService
from .forms import WatermarkForm, ExtractWatermarkForm
from .models import WatermarkedDocument


def index(request):
    if request.method == "POST":
        form = PDFEmailForm(request.POST, request.FILES)
        if form.is_valid():
            # Get the uploaded PDF and email
            pdf_file = request.FILES["pdf_file"]
            email = form.cleaned_data["email"]

            # Convert email to a 10-digit number
            email_number = email_to_number(email)

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

    return render(request, "pdf_app/index.html", {"form": form})


def recover_email(request):
    """
    View to demonstrate the email recovery from the 10-digit number.
    In a real application, you'd need a way to extract the number from the PDF.
    """
    if request.method == "POST":
        # Extract the number from request
        number = request.POST.get("number", "")

        if number and len(number) == 10 and number.isdigit():
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
            return render(request, self.template_name, {"form": form})

        file = request.FILES["file"]

        # Save the file temporarily
        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, file.name)

        with open(temp_path, "wb+") as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        try:
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

            # Handle AJAX requests
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"error": error_message}, status=500)

            # For regular form submissions
            return render(
                request, self.template_name, {"form": form, "error": error_message}
            )
