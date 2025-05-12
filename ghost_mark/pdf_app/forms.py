from django import forms
from .models import WatermarkedDocument


class PDFEmailForm(forms.Form):
    pdf_file = forms.FileField(label="Upload PDF")
    email = forms.EmailField(label="Your Email")


class WatermarkForm(forms.ModelForm):
    """Form for adding watermarks to PDFs."""

    class Meta:
        model = WatermarkedDocument
        fields = ["document", "watermark_text", "watermark_color"]
        widgets = {
            "document": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf"}
            ),
            "watermark_text": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Leave blank for auto-generated ID",
                }
            ),
            "watermark_color": forms.TextInput(
                attrs={
                    "type": "color",
                    "value": "#fffffe",
                    "class": "form-control form-control-color",
                }
            ),
        }
        help_texts = {
            "watermark_text": "Optional. A unique identifier will be generated if left blank.",
            "watermark_color": "Choose a color very close to white (#ffffff) for invisibility.",
        }


class ExtractWatermarkForm(forms.Form):
    """Form for extracting watermarks from PDFs or images."""

    file = forms.FileField(
        label="Select File",
        help_text="Supported formats: PDF, PNG, JPG",
        widget=forms.FileInput(
            attrs={"class": "form-control", "accept": ".pdf,.png,.jpg,.jpeg"}
        ),
    )


class PDFQRCodeForm(forms.Form):
    """Form for adding QR codes with encoded emails to PDFs."""

    pdf_file = forms.FileField(
        label="Upload PDF",
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".pdf"}),
    )
    email = forms.EmailField(
        label="Your Email",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "example@email.com"}
        ),
    )


class QRCodeScanForm(forms.Form):
    """Form for scanning QR codes or manually entering the cipher code."""

    qr_code = forms.FileField(
        label="Upload QR Code Image",
        required=False,
        widget=forms.FileInput(
            attrs={"class": "form-control", "accept": ".png,.jpg,.jpeg"}
        ),
        help_text="Upload an image of the QR code",
    )

    code_string = forms.CharField(
        label="Or Enter Cipher Code Manually",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter the complete cipher code from the QR code",
            }
        ),
        help_text="Enter the code from the QR code if you have it",
    )

    def clean(self):
        cleaned_data = super().clean()
        qr_code = cleaned_data.get("qr_code")
        code_string = cleaned_data.get("code_string")

        if not qr_code and not code_string:
            raise forms.ValidationError(
                "Please either upload a QR code image or enter the code manually."
            )

        return cleaned_data
