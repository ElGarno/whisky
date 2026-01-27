"""Barcode scanning service for whisky bottle recognition."""

import io
from PIL import Image

# Try to import pyzbar, but handle gracefully if not available
try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False


def decode_barcode(image: Image.Image) -> list[dict]:
    """
    Decode barcodes from an image.

    Args:
        image: PIL Image object

    Returns:
        List of decoded barcode dicts with 'data', 'type', and 'rect' keys
    """
    if not PYZBAR_AVAILABLE:
        return []

    # Convert to grayscale for better detection
    if image.mode != 'L':
        gray = image.convert('L')
    else:
        gray = image

    # Decode barcodes
    decoded = pyzbar.decode(gray)

    results = []
    for barcode in decoded:
        results.append({
            'data': barcode.data.decode('utf-8'),
            'type': barcode.type,
            'rect': {
                'left': barcode.rect.left,
                'top': barcode.rect.top,
                'width': barcode.rect.width,
                'height': barcode.rect.height
            }
        })

    return results


def decode_barcode_from_bytes(image_bytes: bytes) -> list[dict]:
    """
    Decode barcodes from image bytes.

    Args:
        image_bytes: Raw image bytes

    Returns:
        List of decoded barcode dicts
    """
    image = Image.open(io.BytesIO(image_bytes))
    return decode_barcode(image)


def get_ean_barcode(barcodes: list[dict]) -> str | None:
    """
    Extract the first EAN barcode from a list of decoded barcodes.

    Args:
        barcodes: List of decoded barcode dicts

    Returns:
        EAN barcode string or None if not found
    """
    for barcode in barcodes:
        # EAN-13, EAN-8, UPC-A are common for whisky bottles
        if barcode['type'] in ('EAN13', 'EAN8', 'UPCA', 'CODE128'):
            return barcode['data']
    return None


def is_available() -> bool:
    """Check if barcode scanning is available."""
    return PYZBAR_AVAILABLE
