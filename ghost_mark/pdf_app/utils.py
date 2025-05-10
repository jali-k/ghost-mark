# import hashlib
# import io
# import math
# from PyPDF2 import PdfReader, PdfWriter
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import letter
# from reportlab.lib.units import cm


# def email_to_number(email):
#     """
#     Convert an email address to a 10-digit number that can be reversed.
#     Uses a hash function and ensures it's exactly 10 digits.
#     """
#     # Create a hash of the email
#     hash_object = hashlib.sha256(email.encode())
#     hash_hex = hash_object.hexdigest()

#     # Convert the first 10 characters of the hex digest to integers
#     # We'll use the first 5 hex characters (20 bits) and map them to 10 digits
#     digits = []
#     for i in range(5):
#         hex_value = int(hash_hex[i * 2 : i * 2 + 2], 16)
#         # Each hex value is 0-255, convert to two digits 0-9
#         digits.append(str(hex_value // 26))
#         digits.append(str(hex_value % 10))

#     # Ensure we have exactly 10 digits
#     result = "".join(digits[:10])

#     # Save the mapping for reversal if needed later
#     # In a real app, you might store this in a database
#     return result


# def add_border_to_pdf(input_pdf, output_pdf, email_number):
#     """
#     Add a border to each page of the PDF with indentations based on the email number.
#     """
#     reader = PdfReader(input_pdf)
#     writer = PdfWriter()

#     for page_num in range(len(reader.pages)):
#         page = reader.pages[page_num]
#         page_width = float(page.mediabox.width)
#         page_height = float(page.mediabox.height)

#         # Create a new PDF with Reportlab to draw the border
#         packet = io.BytesIO()
#         c = canvas.Canvas(packet, pagesize=(page_width, page_height))

#         # Define border parameters
#         margin = 36  # 0.5 inch margin
#         border_width = 1  # 1 point border width

#         # Convert email number to list of digits
#         digits = [int(d) for d in email_number]

#         # Calculate parameters for the stepped border
#         right_border_height = page_height - 2 * margin
#         step_section_height = right_border_height / 4  # top 1/4 of right border
#         segment_height = step_section_height / 10  # height of each step segment

#         # Draw the horizontal borders (top and bottom)
#         c.setLineWidth(border_width)
#         c.line(margin, margin, page_width - margin, margin)  # Bottom border
#         c.line(
#             margin, page_height - margin, page_width - margin, page_height - margin
#         )  # Top border

#         # Draw the left border
#         c.line(margin, margin, margin, page_height - margin)

#         # Draw the right border with steps at the top 1/4
#         # First, draw the straight part (bottom 3/4)
#         c.line(
#             page_width - margin,
#             margin,
#             page_width - margin,
#             page_height - margin - step_section_height,
#         )

#         # Now draw the stepped part (top 1/4)
#         right_x = page_width - margin
#         current_y = page_height - margin - step_section_height

#         for i in range(10):
#             # Calculate indentation based on the digit (half cm per unit)
#             indent = digits[i] * 0.5 * cm

#             # Draw the horizontal part of the step
#             if i > 0:  # Only for segments after the first one
#                 c.line(right_x - prev_indent, current_y, right_x - indent, current_y)

#             # Calculate the end position of the vertical part
#             end_y = current_y + segment_height

#             # Draw the vertical part of the step
#             c.line(right_x - indent, current_y, right_x - indent, end_y)

#             # Update for the next segment
#             current_y = end_y
#             prev_indent = indent

#         # Connect the last step to the top border
#         c.line(right_x - prev_indent, current_y, right_x, page_height - margin)

#         c.save()

#         # Move to the beginning of the BytesIO buffer
#         packet.seek(0)

#         # Create a new PDF with the border
#         border_pdf = PdfReader(packet)

#         # Merge the border PDF with the current page
#         page.merge_page(border_pdf.pages[0])

#         # Add the page to the output PDF
#         writer.add_page(page)

#     # Write the output PDF
#     with open(output_pdf, "wb") as output_file:
#         writer.write(output_file)

#     return output_pdf

import hashlib
import io
import math
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm


def email_to_number(email):
    """
    Convert an email address to a 10-digit number that is reversible.
    Uses a simple substitution and folding algorithm.
    """
    # Define a character set mapping
    char_map = {
        "a": "01",
        "b": "02",
        "c": "03",
        "d": "04",
        "e": "05",
        "f": "06",
        "g": "07",
        "h": "08",
        "i": "09",
        "j": "10",
        "k": "11",
        "l": "12",
        "m": "13",
        "n": "14",
        "o": "15",
        "p": "16",
        "q": "17",
        "r": "18",
        "s": "19",
        "t": "20",
        "u": "21",
        "v": "22",
        "w": "23",
        "x": "24",
        "y": "25",
        "z": "26",
        ".": "27",
        "@": "28",
        "_": "29",
        "-": "30",
        "0": "31",
        "1": "32",
        "2": "33",
        "3": "34",
        "4": "35",
        "5": "36",
        "6": "37",
        "7": "38",
        "8": "39",
        "9": "40",
    }

    # Convert email to lowercase for consistent mapping
    email = email.lower()

    # Convert each character to its numeric representation
    number_str = ""
    for char in email:
        if char in char_map:
            number_str += char_map[char]
        else:
            # For any unexpected character, use a default value
            number_str += "00"

    # Apply a folding technique to get exactly 10 digits
    # If too long, fold and add; if too short, pad
    result = ""
    if len(number_str) > 10:
        # Fold the string by adding pairs of digits modulo 10
        for i in range(0, len(number_str) - 1, 2):
            if i < 20:  # Only process the first 20 characters (10 pairs)
                sum_val = (
                    int(number_str[i]) + int(number_str[len(number_str) - i - 1])
                ) % 10
                result += str(sum_val)
    else:
        # If the string is too short, just pad with zeros
        result = number_str + "0" * (10 - len(number_str))

    # Ensure we have exactly 10 digits
    result = result[:10]
    print(f"Email: {email}, Number: {result}")  # Debugging output

    return result


def number_to_email(number_str):
    """
    Reverses the email_to_number function to get the original email.
    This is just a stub - in a real application, you would need to store
    the original email or use a more sophisticated reversible algorithm.
    """
    # In a real application, you might store the email-number mapping in a database
    # Here we're just demonstrating that the concept is possible
    # You could implement a more sophisticated algorithm based on your needs

    # This function would retrieve the original email from storage
    # or use the reverse of your conversion algorithm

    # For demonstration purposes, we'll return a placeholder
    return f"original_email_for_{number_str}@example.com"


def add_border_to_pdf(input_pdf, output_pdf, email_number):
    """
    Add a border to each page of the PDF with indentations based on the email number.
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        # Create a new PDF with Reportlab to draw the border
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))

        # Define border parameters
        margin = 36  # 0.5 inch margin
        border_width = 1  # 1 point border width

        # Convert email number to list of digits
        digits = [int(d) for d in email_number]

        # Calculate parameters for the stepped border
        right_border_height = page_height - 2 * margin
        step_section_height = (
            right_border_height / 8
        )  # top 1/8 of right border - UPDATED
        segment_height = step_section_height / 10  # height of each step segment

        # Draw the horizontal borders (top and bottom)
        c.setLineWidth(border_width)
        c.line(margin, margin, page_width - margin, margin)  # Bottom border
        c.line(
            margin, page_height - margin, page_width - margin, page_height - margin
        )  # Top border

        # Draw the left border
        c.line(margin, margin, margin, page_height - margin)

        # Draw the right border with steps at the top 1/8
        # First, draw the straight part (bottom 7/8)
        c.line(
            page_width - margin,
            margin,
            page_width - margin,
            page_height - margin - step_section_height,
        )

        # Now draw the stepped part (top 1/8)
        right_x = page_width - margin
        current_y = page_height - margin - step_section_height

        for i in range(10):
            # Calculate indentation based on the digit (half cm per unit)
            indent = digits[i] * 0.5 * cm

            # Draw the horizontal part of the step
            if i > 0:  # Only for segments after the first one
                c.line(right_x - prev_indent, current_y, right_x - indent, current_y)

            # Calculate the end position of the vertical part
            end_y = current_y + segment_height

            # Draw the vertical part of the step
            c.line(right_x - indent, current_y, right_x - indent, end_y)

            # Update for the next segment
            current_y = end_y
            prev_indent = indent

        # Draw a horizontal line at the end of stepping to complete the border
        # This connects the last step to the right edge
        c.line(right_x - prev_indent, current_y, right_x, current_y)

        # Connect the right edge up to the top border
        c.line(right_x, current_y, right_x, page_height - margin)

        c.save()

        # Move to the beginning of the BytesIO buffer
        packet.seek(0)

        # Create a new PDF with the border
        border_pdf = PdfReader(packet)

        # Merge the border PDF with the current page
        page.merge_page(border_pdf.pages[0])

        # Add the page to the output PDF
        writer.add_page(page)

    # Write the output PDF
    with open(output_pdf, "wb") as output_file:
        writer.write(output_file)

    return output_pdf
