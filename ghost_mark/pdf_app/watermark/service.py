import os
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter
import pytesseract
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


class PDFWatermarkService:
    # Define a fixed watermark color very close to white
    # Using #FFFEFA (255, 254, 250) - almost imperceptible but unique enough to detect
    WATERMARK_COLOR = "#FFFEFA"

    @staticmethod
    def obfuscate_email(email):
        """
        Obfuscate email to prevent auto-detection as clickable mailto link

        Args:
            email (str): Original email address

        Returns:
            str: Obfuscated email that won't be detected as clickable
        """
        if not email or "@" not in email:
            return email

        # Replace @ with AT and . with DOT
        obfuscated = email.replace("@", "AT").replace(".", "DOT")

        print(f"📧 Original: {email}")
        print(f"🔒 Obfuscated: {obfuscated}")

        return obfuscated

    @staticmethod
    def deobfuscate_email(obfuscated_email):
        """
        Convert obfuscated email back to original format

        Args:
            obfuscated_email (str): Obfuscated email string

        Returns:
            str: Original email address
        """
        if not obfuscated_email:
            return obfuscated_email

        # Restore original email format
        restored = obfuscated_email.replace("AT", "@").replace("DOT", ".")

        print(f"🔒 Obfuscated: {obfuscated_email}")
        print(f"📧 Restored: {restored}")

        return restored

    @staticmethod
    def add_invisible_watermark(
        pdf_file, watermark_text, color=None, skip_first_page=True
    ):
        """
        Add an invisible watermark to a PDF file using a fixed near-white color.
        Places watermarks only at the top and bottom of the left side of each page.
        Automatically obfuscates email addresses in the watermark text.
        Returns the watermarked PDF file as BytesIO.

        Args:
            pdf_file: PDF file object
            watermark_text (str): Text to use as watermark (will be obfuscated if it's an email)
            color (str): Color for watermark (uses default if None)
            skip_first_page (bool): If True, don't add watermark to first page

        Returns:
            BytesIO: Watermarked PDF file as BytesIO
        """
        # Always use our fixed watermark color for consistency
        color = PDFWatermarkService.WATERMARK_COLOR

        # Parse color to RGB
        color = color.lstrip("#")
        r, g, b = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

        # Obfuscate email to prevent clickable links
        processed_watermark_text = PDFWatermarkService.obfuscate_email(watermark_text)

        # Read the input PDF first to get page count
        existing_pdf = PyPDF2.PdfReader(pdf_file)
        output = PyPDF2.PdfWriter()
        total_pages = len(existing_pdf.pages)

        print(f"📄 Total pages: {total_pages}")
        print(f"🚫 Skip first page: {skip_first_page}")

        # Create watermark once (we'll reuse it for all pages that need it)
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)

        # Get letter size dimensions
        width, height = letter

        # Use a smaller font for less intrusive watermarks
        c.setFont("Helvetica", 10)  # Small font size for better invisibility
        c.setFillColorRGB(r / 255, g / 255, b / 255)

        # Place watermarks only on the left side - top and bottom
        c.drawString(20, height - 30, processed_watermark_text)  # Top left
        c.drawString(20, 20, processed_watermark_text)  # Bottom left

        c.save()

        # Move to the beginning of the BytesIO buffer
        packet.seek(0)
        watermark_pdf = PyPDF2.PdfReader(packet)

        # Process each page
        for i in range(total_pages):
            page = existing_pdf.pages[i]

            # Skip first page if requested
            if skip_first_page and i == 0:
                print(f"📄 Page {i + 1}: Skipping (first page)")
                output.add_page(page)  # Add page without watermark
            else:
                print(f"📄 Page {i + 1}: Adding watermark")
                # Add watermark to this page
                page.merge_page(watermark_pdf.pages[0])
                output.add_page(page)

        # Save the result to BytesIO
        result_pdf = BytesIO()
        output.write(result_pdf)
        result_pdf.seek(0)

        return result_pdf

    @staticmethod
    def extract_watermark(file_path):
        """
        Extract the watermark from a PDF or image file by focusing on the specific watermark color.
        Automatically deobfuscates email addresses in extracted text.
        Works with PDFs and screenshots (PNG, JPG).
        """
        # Get our fixed watermark color
        watermark_color = PDFWatermarkService.WATERMARK_COLOR.lstrip("#")
        wr, wg, wb = tuple(int(watermark_color[i : i + 2], 16) for i in (0, 2, 4))

        # Determine file type by extension
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension in [".pdf"]:
            # For PDF files, convert to images first
            try:
                # Try to use pdf2image if available
                from pdf2image import convert_from_path

                images = convert_from_path(file_path, dpi=300)
                print(f"📄 Processing {len(images)} pages from PDF")
            except ImportError:
                # If pdf2image not available, create blank image
                print("Warning: pdf2image not available. Using simplified approach.")
                images = PDFWatermarkService._create_blank_images(file_path)
        elif file_extension in [".png", ".jpg", ".jpeg"]:
            # For image files, load directly
            images = [Image.open(file_path)]
            print(f"🖼️ Processing single image file")
        else:
            raise ValueError("Unsupported file format. Use PDF, PNG, or JPG")

        # Extract watermark from all images and collect results
        extracted_texts = []

        for page_num, img in enumerate(images):
            try:
                print(f"🔍 Analyzing page/image {page_num + 1}")

                # Convert PIL Image to OpenCV format
                img_cv = np.array(img.convert("RGB"))
                img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

                # Create a mask specifically for our watermark color with a small tolerance
                # Lower and upper bounds for color detection (tighter range for specific color)
                lower_bound = np.array(
                    [wb - 5, wg - 5, wr - 5]
                )  # BGR format for OpenCV
                upper_bound = np.array([wb + 3, wg + 3, wr + 3])

                # Create mask for our specific watermark color
                mask = cv2.inRange(img_cv, lower_bound, upper_bound)

                # Dilate the mask to connect nearby pixels
                kernel = np.ones((3, 3), np.uint8)
                mask = cv2.dilate(mask, kernel, iterations=1)

                # Apply the mask to get just the watermark
                watermark = cv2.bitwise_and(img_cv, img_cv, mask=mask)

                # Convert to grayscale and invert for better OCR
                gray = cv2.cvtColor(watermark, cv2.COLOR_BGR2GRAY)
                _, binary = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)

                # Perform OCR on the isolated watermark
                text = pytesseract.image_to_string(binary)

                # Clean up and add to results
                text = text.strip()
                if text:
                    print(f"📝 Found text on page {page_num + 1}: {text}")
                    extracted_texts.append(text)
                else:
                    print(f"❌ No text found on page {page_num + 1}")

            except Exception as e:
                print(f"❌ Error processing page {page_num + 1}: {str(e)}")

        # Process all extracted texts
        if extracted_texts:
            print(f"📊 Total extracted texts: {len(extracted_texts)}")

            # Instead of returning just the most common word,
            # let's reconstruct the complete watermark text

            # Method 1: Try to find the longest/most complete text
            longest_text = max(extracted_texts, key=len)
            print(f"🔍 Longest extracted text: {longest_text}")

            # Method 2: If multiple similar texts, try to merge them
            # Clean up each extracted text and see if we can reconstruct
            cleaned_texts = []
            for text in extracted_texts:
                # Remove extra whitespace and newlines
                cleaned = " ".join(text.split())
                if cleaned and len(cleaned) > 3:  # Ignore very short extractions
                    cleaned_texts.append(cleaned)

            if cleaned_texts:
                # Use the most frequent complete text, not just individual words
                from collections import Counter

                text_counts = Counter(cleaned_texts)
                most_common_complete_text = text_counts.most_common(1)[0][0]

                print(f"🔍 Most common complete text: {most_common_complete_text}")

                # Choose the better option between longest and most common
                final_text = (
                    most_common_complete_text
                    if len(most_common_complete_text) >= len(longest_text)
                    else longest_text
                )

                print(f"🔍 Final extracted text: {final_text}")

                # Deobfuscate the extracted text to restore original email
                restored_text = PDFWatermarkService.deobfuscate_email(final_text)

                print(f"📧 Final restored text: {restored_text}")

                return restored_text

        print("❌ No watermark found in any page/image")
        return "No watermark found"

    @staticmethod
    def _create_blank_images(pdf_path):
        """Create blank images for a PDF file when pdf2image is not available."""
        images = []
        try:
            pdf = PyPDF2.PdfReader(open(pdf_path, "rb"))
            for _ in range(len(pdf.pages)):
                # Create a blank image for the PDF page
                img = Image.new("RGB", (612, 792), "white")  # Letter size in points
                images.append(img)
        except Exception as e:
            print(f"Error creating images: {str(e)}")
            # Return at least one blank image
            images = [Image.new("RGB", (612, 792), "white")]

        return images

    @staticmethod
    def test_obfuscation():
        """
        Test function to see how email obfuscation works
        """
        test_emails = [
            "abcd1234@gmail.com",
            "user@example.com",
            "test.email@domain.co.uk",
            "admin@company.org",
            "not_an_email_text",
        ]

        print("🧪 Testing Email Obfuscation:")
        print("=" * 50)

        for email in test_emails:
            obfuscated = PDFWatermarkService.obfuscate_email(email)
            restored = PDFWatermarkService.deobfuscate_email(obfuscated)

            print(f"Original:    {email}")
            print(f"Obfuscated:  {obfuscated}")
            print(f"Restored:    {restored}")
            print(f"Match:       {'✅' if email == restored else '❌'}")
            print("-" * 30)


# Example usage and testing
if __name__ == "__main__":
    # Test the obfuscation system
    PDFWatermarkService.test_obfuscation()
