"""Convert uploaded raster images into PDF pages for the existing OCR pipeline."""

import cv2
import fitz
import numpy as np

from app.exceptions import BankStatementError


def image_bytes_to_pdf(image_bytes: bytes, dpi: int = 300) -> bytes:
    """Decode an image upload and embed it in a single-page PDF."""
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise BankStatementError(
            "The uploaded image could not be decoded.",
            "Please upload a valid PNG, JPEG, WEBP, BMP, or TIFF image.",
        )

    encoded, png_bytes = cv2.imencode(".png", image)
    if not encoded:
        raise BankStatementError("The uploaded image could not be converted for OCR.")

    height, width = image.shape[:2]
    page_width = width * 72 / dpi
    page_height = height * 72 / dpi
    document = fitz.open()
    page = document.new_page(width=page_width, height=page_height)
    page.insert_image(page.rect, stream=png_bytes.tobytes())
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes