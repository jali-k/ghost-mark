import hashlib
import io
import math
import qrcode
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


def email_to_cipher(email):
    """
    Convert an email address to a cipher string:
    1. Extract the part before @ sign
    2. Apply Caesar cipher with shift 8
    3. Add prefix and suffix for additional obfuscation

    Args:
        email: The email address to encode

    Returns:
        A cipher string that can be decoded back to the original email
    """
    # Extract the part before @ sign
    if "@" in email:
        username = email.split("@")[0]
        domain = email.split("@")[1]
    else:
        username = email
        domain = "example.com"  # Default domain if @ is not present

    # Define characters for the Caesar cipher (alphanumeric and common symbols)
    charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-+="
    charset_length = len(charset)

    # Apply Caesar cipher with shift 8
    cipher_text = ""
    for char in username:
        if char in charset:
            # Find the index of the character in our charset
            index = charset.find(char)
            # Apply shift of 8
            new_index = (index + 8) % charset_length
            # Add the shifted character to the cipher text
            cipher_text += charset[new_index]
        else:
            # Keep characters not in our charset unchanged
            cipher_text += char

    # Add the prefix and suffix
    final_cipher = "rt567^#EF5" + cipher_text + "y7%$y[="

    # Store the domain information (for decoding later)
    # We'll append it in a format that's easy to parse but not obvious
    domain_encoded = ""
    for char in domain:
        if char in charset:
            index = charset.find(char)
            new_index = (index + 8) % charset_length
            domain_encoded += charset[new_index]
        else:
            domain_encoded += char

    # Join the entire thing with a separator that's unlikely to be in either part
    complete_cipher = final_cipher + "||" + domain_encoded

    return complete_cipher


def cipher_to_email(cipher_string):
    """
    Decode a cipher string back to the original email address.

    Args:
        cipher_string: The cipher string created by email_to_cipher

    Returns:
        The original email address
    """
    # Split to get domain part if it exists
    parts = cipher_string.split("||")
    cipher_text = parts[0]

    # Remove prefix and suffix
    prefix = "rt567^#EF5"
    suffix = "y7%$y[="

    if cipher_text.startswith(prefix) and cipher_text.endswith(suffix):
        # Remove prefix and suffix
        cipher_text = cipher_text[len(prefix) : -len(suffix)]
    else:
        # If prefix or suffix is missing, this might not be a valid cipher
        raise ValueError("Invalid cipher format. Prefix or suffix missing.")

    # Define the same charset as in encoding
    charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-+="
    charset_length = len(charset)

    # Reverse the Caesar cipher with shift 8
    plain_text = ""
    for char in cipher_text:
        if char in charset:
            # Find the index of the character in our charset
            index = charset.find(char)
            # Apply reverse shift of 8
            new_index = (index - 8) % charset_length
            # Add the unshifted character to the plain text
            plain_text += charset[new_index]
        else:
            # Keep characters not in our charset unchanged
            plain_text += char

    # Decode the domain part if it exists
    if len(parts) > 1:
        domain_encoded = parts[1]
        domain = ""
        for char in domain_encoded:
            if char in charset:
                index = charset.find(char)
                new_index = (index - 8) % charset_length
                domain += charset[new_index]
            else:
                domain += char

        # Reconstruct the full email
        email = plain_text + "@" + domain
    else:
        # If domain part is missing, use just the username
        email = plain_text + "@example.com"

    return email


def generate_qr_code(data, box_size=5, border=1):
    """
    Generate a QR code from the provided data

    Args:
        data: The data to encode in the QR code
        box_size: Size of each box in the QR code (default: 5)
        border: Border size in boxes (default: 1)

    Returns:
        BytesIO object containing the QR code image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Save the image to a BytesIO object
    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)

    return buffer


def add_qr_code_to_pdf(input_pdf, output_pdf, email):
    """
    Add a QR code to the bottom right corner of each page of the PDF using our cipher

    Args:
        input_pdf: Input PDF file path or file-like object
        output_pdf: Output PDF file path
        email: The email address to encode in the QR code

    Returns:
        Path to the output PDF
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    # Encode the email using our new cipher and generate QR code
    encoded_data = email_to_cipher(email)
    qr_buffer = generate_qr_code(encoded_data, box_size=3, border=1)

    # Create a temporary file to save the QR code image
    temp_qr_path = "temp_qr_code.png"
    with open(temp_qr_path, "wb") as f:
        f.write(qr_buffer.getvalue())

    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        # Create a new PDF with Reportlab to draw the QR code
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))

        # Define QR code parameters
        qr_size = 50  # Size of QR code in points (approximately 0.7 inch)
        margin = 20  # Margin from the edge in points

        # Place the QR code at the bottom right corner
        c.drawImage(
            temp_qr_path,
            page_width - qr_size - margin,  # X position
            margin,  # Y position
            width=qr_size,
            height=qr_size,
        )

        c.save()

        # Move to the beginning of the BytesIO buffer
        packet.seek(0)

        # Create a new PDF with the QR code
        qr_pdf = PdfReader(packet)

        # Merge the QR code PDF with the current page
        page.merge_page(qr_pdf.pages[0])

        # Add the page to the output PDF
        writer.add_page(page)

    # Write the output PDF
    with open(output_pdf, "wb") as output_file:
        writer.write(output_file)

    # Clean up the temporary QR code image
    import os

    if os.path.exists(temp_qr_path):
        os.remove(temp_qr_path)

    return output_pdf


def process_qr_code(qr_data):
    """
    Process the data from a QR code and extract the email.

    Args:
        qr_data: String data extracted from QR code

    Returns:
        Dictionary with original email and encoded data
    """
    try:
        # Attempt to decode the cipher string to an email
        email = cipher_to_email(qr_data)

        return {"code": qr_data, "email": email}
    except Exception as e:
        # If decoding fails, raise an error
        raise ValueError(f"Failed to decode QR code data: {str(e)}")
