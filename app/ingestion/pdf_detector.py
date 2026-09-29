"""PDF type detection — text-based vs image-based (scanned).

Strategy:
    1. Open PDF with pdfplumber (lightweight text extraction).
    2. Sample pages and check if meaningful text exists.
    3. If yes → text PDF. If no → scanned PDF.
    4. OCR is only triggered later, and only for scanned PDFs.
"""

import pdfplumber


# Minimum characters per page to consider it a text PDF
_MIN_CHARS_PER_PAGE = 50

# Max pages to sample for detection (no need to scan entire doc)
_SAMPLE_PAGES = 3


def detect_pdf_type(pdf_path: str) -> str:
    """Detect whether a PDF is text-based or image-based (scanned).

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        "text" if meaningful text can be extracted directly,
        "image" if the PDF appears to be scanned / image-based.
    """
    with pdfplumber.open(pdf_path) as pdf:
        pages_to_check = pdf.pages[:_SAMPLE_PAGES]

        for page in pages_to_check:
            text = page.extract_text() or ""
            # Strip whitespace and check for meaningful content
            if len(text.strip()) >= _MIN_CHARS_PER_PAGE:
                return "text"

    return "image"


def get_page_count(pdf_path: str) -> int:
    """Return the total number of pages in the PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)
