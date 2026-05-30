import qrcode
import os


def generate_qr_code(data: str, file_path: str) -> None:
    """Generate a QR code image.

    Args:
        data: The string data to encode (e.g., UPI payment string).
        file_path: Full absolute path where the PNG will be saved.
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(file_path)
