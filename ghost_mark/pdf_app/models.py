from django.db import models

# Create your models here.


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
