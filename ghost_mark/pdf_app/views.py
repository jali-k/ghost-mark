# import os
# import uuid
# from django.shortcuts import render
# from django.http import FileResponse
# from django.conf import settings
# from .forms import PDFEmailForm
# from .utils import email_to_number, add_border_to_pdf


# def index(request):
#     if request.method == "POST":
#         form = PDFEmailForm(request.POST, request.FILES)
#         if form.is_valid():
#             # Get the uploaded PDF and email
#             pdf_file = request.FILES["pdf_file"]
#             email = form.cleaned_data["email"]

#             # Convert email to a 10-digit number
#             email_number = email_to_number(email)

#             # Create a unique filename for the output PDF
#             output_filename = f"border_{uuid.uuid4().hex}.pdf"
#             output_path = os.path.join(settings.MEDIA_ROOT, output_filename)

#             # Save the uploaded PDF temporarily
#             temp_pdf_path = os.path.join(
#                 settings.MEDIA_ROOT, f"temp_{uuid.uuid4().hex}.pdf"
#             )
#             with open(temp_pdf_path, "wb+") as destination:
#                 for chunk in pdf_file.chunks():
#                     destination.write(chunk)

#             # Process the PDF, adding borders
#             add_border_to_pdf(temp_pdf_path, output_path, email_number)

#             # Clean up the temporary file
#             os.unlink(temp_pdf_path)

#             # Return the processed PDF as a download
#             return FileResponse(
#                 open(output_path, "rb"),
#                 as_attachment=True,
#                 filename=f"bordered_{pdf_file.name}",
#             )
#     else:
#         form = PDFEmailForm()

#     return render(request, "pdf_app/index.html", {"form": form})

import os
import uuid
from django.shortcuts import render
from django.http import FileResponse, HttpResponse
from django.conf import settings
from .forms import PDFEmailForm
from .utils import email_to_number, number_to_email, add_border_to_pdf


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
