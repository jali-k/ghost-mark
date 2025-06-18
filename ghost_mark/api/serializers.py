# api/serializers.py
from rest_framework import serializers
import uuid


class WatermarkSerializer(serializers.Serializer):
    pdf_file = serializers.FileField()
    watermark_text = serializers.CharField(
        max_length=255,  allow_blank=True
    )

    def validate_pdf_file(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are allowed.")
        return value

    def validate_watermark_text(self, value):
        if not value:
            raise serializers.ValidationError("Watermark text is required.")
        return value


class QRCodeSerializer(serializers.Serializer):
    pdf_file = serializers.FileField()
    email = serializers.EmailField()

    def validate_pdf_file(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are allowed.")
        return value


class FontSteganographySerializer(serializers.Serializer):
    pdf_file = serializers.FileField()
    secret_message = serializers.CharField(max_length=200)
    cover_text = serializers.CharField()

    def validate_pdf_file(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are allowed.")
        return value

    def validate(self, data):
        secret_message = data.get("secret_message", "")
        cover_text = data.get("cover_text", "")

        if secret_message and cover_text:
            # Calculate required characters
            message_bits = len(secret_message) * 8
            non_space_chars = len([char for char in cover_text if char != " "])

            if message_bits > non_space_chars:
                raise serializers.ValidationError(
                    {
                        "cover_text": f"Cover text too short! Your message needs {message_bits} characters "
                        f"but your cover text only has {non_space_chars} non-space characters."
                    }
                )

        return data


class CombinedSteganographySerializer(serializers.Serializer):
    pdf_file = serializers.FileField()

    # Watermark fields (optional)
    enable_watermark = serializers.BooleanField(default=False)
    watermark_text = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )

    # QR Code fields (optional)
    enable_qr_code = serializers.BooleanField(default=False)
    email = serializers.EmailField(required=False, allow_blank=True)

    # Font Steganography fields (optional)
    enable_font_stego = serializers.BooleanField(default=False)
    secret_message = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    cover_text = serializers.CharField(required=False, allow_blank=True)

    def validate_pdf_file(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are allowed.")
        return value

    def validate(self, data):
        # Check if at least one method is enabled
        if not any(
            [
                data.get("enable_watermark"),
                data.get("enable_qr_code"),
                data.get("enable_font_stego"),
            ]
        ):
            raise serializers.ValidationError(
                "At least one steganography method must be enabled."
            )

        # Validate QR code fields
        if data.get("enable_qr_code") and not data.get("email"):
            raise serializers.ValidationError(
                {"email": "Email is required when QR code is enabled."}
            )

        # Validate font steganography fields
        if data.get("enable_font_stego"):
            if not data.get("secret_message"):
                raise serializers.ValidationError(
                    {
                        "secret_message": "Secret message is required when font steganography is enabled."
                    }
                )
            if not data.get("cover_text"):
                raise serializers.ValidationError(
                    {
                        "cover_text": "Cover text is required when font steganography is enabled."
                    }
                )

            # Validate cover text length
            secret_message = data.get("secret_message", "")
            cover_text = data.get("cover_text", "")
            message_bits = len(secret_message) * 8
            non_space_chars = len([char for char in cover_text if char != " "])

            if message_bits > non_space_chars:
                raise serializers.ValidationError(
                    {
                        "cover_text": f"Cover text too short! Your message needs {message_bits} characters "
                        f"but your cover text only has {non_space_chars} non-space characters."
                    }
                )

        # Set default watermark text if watermark is enabled but no text provided
        if data.get("enable_watermark") and not data.get("watermark_text"):
            raise serializers.ValidationError(
                {
                    "watermark_text": "Watermark text is required when watermarking is enabled."
                }
            )

        return data


class SelectedSteganographySerializer(serializers.Serializer):
    pdf_file = serializers.FileField()
    methods = serializers.ListField(
        child=serializers.ChoiceField(choices=["watermark", "qr_code", "font_stego"]),
        min_length=1,
    )

    # Optional fields for each method
    watermark_text = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    secret_message = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    cover_text = serializers.CharField(required=False, allow_blank=True)

    def validate_pdf_file(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are allowed.")
        return value

    def validate(self, data):
        methods = data.get("methods", [])

        # Validate required fields for selected methods
        if "qr_code" in methods and not data.get("email"):
            raise serializers.ValidationError(
                {"email": "Email is required when qr_code method is selected."}
            )

        if "font_stego" in methods:
            if not data.get("secret_message"):
                raise serializers.ValidationError(
                    {
                        "secret_message": "Secret message is required when font_stego method is selected."
                    }
                )
            if not data.get("cover_text"):
                raise serializers.ValidationError(
                    {
                        "cover_text": "Cover text is required when font_stego method is selected."
                    }
                )

            # Validate cover text length
            secret_message = data.get("secret_message", "")
            cover_text = data.get("cover_text", "")
            message_bits = len(secret_message) * 8
            non_space_chars = len([char for char in cover_text if char != " "])

            if message_bits > non_space_chars:
                raise serializers.ValidationError(
                    {
                        "cover_text": f"Cover text too short! Your message needs {message_bits} characters "
                        f"but your cover text only has {non_space_chars} non-space characters."
                    }
                )

        # Set default watermark text if watermark is selected but no text provided
        if "watermark" in methods and not data.get("watermark_text"):
            raise serializers.ValidationError(
                {"watermark_text": "Watermark text is required when watermarking is enabled."}
            )

        return data
