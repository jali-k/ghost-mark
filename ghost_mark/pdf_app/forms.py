from django import forms


class PDFEmailForm(forms.Form):
    pdf_file = forms.FileField(label="Upload PDF")
    email = forms.EmailField(label="Your Email")
