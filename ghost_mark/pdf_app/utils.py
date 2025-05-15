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
    Convert the first 10 valid characters of an email to a 20-digit number.
    Each character maps to a 2-digit number (01-40).
    Skip any characters not in the mapping.
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

    # Get the first 10 valid characters (skip invalid ones)
    result = ""
    encoded_chars = []

    for char in email:
        if char in char_map:
            if len(encoded_chars) < 10:  # Only take the first 10 valid characters
                encoded_chars.append(char)
                result += char_map[char]  # Take both digits this time

    # Pad if necessary to ensure we have exactly 20 digits
    result = result + "00" * (10 - len(result) // 2)

    # Ensure we have exactly 20 digits
    result = result[:20]

    return result, encoded_chars


def number_to_email(number_str):
    """
    Decode the 20-digit number back to the original 10 characters of the email.
    Takes 2 digits at a time to map back to characters.
    """
    # Define the reverse character mapping
    char_map = {
        "01": "a",
        "02": "b",
        "03": "c",
        "04": "d",
        "05": "e",
        "06": "f",
        "07": "g",
        "08": "h",
        "09": "i",
        "10": "j",
        "11": "k",
        "12": "l",
        "13": "m",
        "14": "n",
        "15": "o",
        "16": "p",
        "17": "q",
        "18": "r",
        "19": "s",
        "20": "t",
        "21": "u",
        "22": "v",
        "23": "w",
        "24": "x",
        "25": "y",
        "26": "z",
        "27": ".",
        "28": "@",
        "29": "_",
        "30": "-",
        "31": "0",
        "32": "1",
        "33": "2",
        "34": "3",
        "35": "4",
        "36": "5",
        "37": "6",
        "38": "7",
        "39": "8",
        "40": "9",
    }

    # Decode each pair of digits back to its original character
    decoded_email = ""

    # Process the string 2 digits at a time
    for i in range(0, len(number_str), 2):
        if i + 1 < len(number_str):  # Ensure we have 2 digits
            pair = number_str[i : i + 2]
            decoded_email += char_map.get(pair, "?")

    return decoded_email


def add_border_to_pdf(input_pdf, output_pdf, email_number):
    """
    Add a border to each page of the PDF with indentations based on the email number.
    Uses 1/16 of page height and adds dots to count steps.
    Processes the 20-digit number 2 digits at a time for 10 pairs.
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

        # Process email number as pairs of digits (01-40)
        digit_pairs = []
        for i in range(0, len(email_number), 2):
            if i + 1 < len(email_number):
                pair = email_number[i : i + 2]
                digit_pairs.append(int(pair))
            else:
                digit_pairs.append(0)  # Default for incomplete pair

        # Make sure we have 10 pairs
        while len(digit_pairs) < 10:
            digit_pairs.append(0)
        digit_pairs = digit_pairs[:10]  # Take only the first 10 pairs

        print("Processing digit pairs:", digit_pairs)  # Debug print

        # Calculate parameters for the stepped border
        right_border_height = page_height - 2 * margin
        step_section_height = right_border_height / 16  # Using 1/16 of height
        segment_height = step_section_height / 10  # height of each step segment

        # Draw the horizontal borders (top and bottom)
        c.setLineWidth(border_width)
        c.line(margin, margin, page_width - margin, margin)  # Bottom border
        c.line(
            margin, page_height - margin, page_width - margin, page_height - margin
        )  # Top border

        # Draw the left border
        c.line(margin, margin, margin, page_height - margin)

        # Draw the right border with steps at the top 1/16
        # First, draw the straight part (bottom 15/16)
        c.line(
            page_width - margin,
            margin,
            page_width - margin,
            page_height - margin - step_section_height,
        )

        # Define a smaller step size for up to 40 steps
        step_size = 0.125 * cm  # 1/4 of 0.5cm

        # Draw reference dots at every 5 steps (5, 10, 15, etc)
        dot_size = 0.75  # Very tiny dots
        for step in range(5, 41, 5):
            dot_x = page_width - margin - step * step_size
            dot_y = page_height - margin + 5
            c.circle(dot_x, dot_y, dot_size, fill=1)
            c.setFont("Helvetica", 4)
            c.drawString(dot_x - 2, dot_y + 5, str(step))

        # Now draw the stepped part (top 1/16)
        right_x = page_width - margin
        current_y = page_height - margin - step_section_height

        # Process each digit pair (total of 10 pairs)
        for i in range(10):
            # Get the value from the digit pair (01-40)
            pair_value = digit_pairs[i]

            # Calculate indentation based on the digit pair
            indent = pair_value * step_size

            # Draw the horizontal part of the step
            if i > 0:  # Only for segments after the first one
                c.line(right_x - prev_indent, current_y, right_x - indent, current_y)

            # Calculate the end position of the vertical part
            end_y = current_y + segment_height

            # Draw the vertical part of the step
            c.line(right_x - indent, current_y, right_x - indent, end_y)

            # Draw a dot for this specific step position
            dot_x = right_x - indent
            dot_y = page_height - margin + 10
            c.circle(dot_x, dot_y, 1.5, fill=1)

            # Add the digit pair value
            c.setFont("Helvetica", 6)
            c.drawString(dot_x - 3, dot_y + 8, str(pair_value))

            # Update for the next segment
            current_y = end_y
            prev_indent = indent

        # Draw a horizontal line at the end of stepping to complete the border
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
