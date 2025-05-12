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
    def add_invisible_watermark(pdf_file, watermark_text, color=None):
        """
        Add an invisible watermark to a PDF file using a fixed near-white color.
        Places watermarks closer to the page corners.
        Returns the watermarked PDF file as BytesIO.
        """
        # Always use our fixed watermark color for consistency
        color = PDFWatermarkService.WATERMARK_COLOR

        # Parse color to RGB
        color = color.lstrip("#")
        r, g, b = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

        # Create a watermark
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)

        # Get letter size dimensions
        width, height = letter

        # Use a smaller font for less intrusive watermarks
        c.setFont("Helvetica", 10)  # Reduced from 24 to 18
        c.setFillColorRGB(r / 255, g / 255, b / 255)

        # Remove the center watermark and place watermarks closer to the corners
        # Draw at each corner - closer to the actual corners
        c.drawString(
            20, 20, watermark_text
        )  # Bottom left - moved from (50,50) to (20,20)
        c.drawString(
            width - 150, 20, watermark_text
        )  # Bottom right - moved from (width-200,50) to (width-150,20)
        c.drawString(
            20, height - 30, watermark_text
        )  # Top left - moved from (50,height-50) to (20,height-30)
        c.drawString(
            width - 150, height - 30, watermark_text
        )  # Top right - moved from (width-200,height-50) to (width-150,height-30)

        c.save()

        # Move to the beginning of the BytesIO buffer
        packet.seek(0)
        watermark_pdf = PyPDF2.PdfReader(packet)

        # Read the input PDF
        existing_pdf = PyPDF2.PdfReader(pdf_file)
        output = PyPDF2.PdfWriter()

        # Add the watermark to each page
        for i in range(len(existing_pdf.pages)):
            page = existing_pdf.pages[i]
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
            except ImportError:
                # If pdf2image not available, create blank image
                print("Warning: pdf2image not available. Using simplified approach.")
                images = PDFWatermarkService._create_blank_images(file_path)
        elif file_extension in [".png", ".jpg", ".jpeg"]:
            # For image files, load directly
            images = [Image.open(file_path)]
        else:
            raise ValueError("Unsupported file format. Use PDF, PNG, or JPG")

        # Extract watermark from all images and collect results
        extracted_texts = []

        for img in images:
            try:
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
                    extracted_texts.append(text)

                # Debug: Save masked image to see what's being processed
                # cv2.imwrite("watermark_masked.png", binary)
            except Exception as e:
                print(f"Error processing image: {str(e)}")

        # Process all extracted texts
        if extracted_texts:
            # Return the most common text found
            from collections import Counter

            # Flatten and clean the extracted text
            all_words = []
            for text in extracted_texts:
                for line in text.splitlines():
                    words = line.split()
                    all_words.extend(
                        [w for w in words if len(w) > 2]
                    )  # Only consider words with length > 2

            if all_words:
                word_counts = Counter(all_words)
                most_common = word_counts.most_common(1)[0][0]
                return most_common

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
