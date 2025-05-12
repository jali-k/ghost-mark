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
