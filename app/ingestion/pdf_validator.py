"""Pre-flight validation for uploaded PDF bank statements.

Validates document integrity before extraction starts:
- Valid PDF magic bytes (%PDF-)
- Non-empty payload
- Password protection / encryption detection
- File corruption detection
"""

import os
import fitz  # PyMuPDF

from app.exceptions import (
    InvalidPDFError,
    PasswordProtectedPDFError,
    EmptyPDFError,
    CorruptedPDFError,
)


def validate_pdf_file(pdf_path: str) -> fitz.Document:
    """Validate PDF file structure and integrity.

    Args:
        pdf_path: Path to the target PDF file on disk.

    Returns:
        Opened PyMuPDF Document if valid.

    Raises:
        EmptyPDFError: If file is missing or 0 bytes.
        InvalidPDFError: If file lacks valid PDF header magic bytes.
        PasswordProtectedPDFError: If file is encrypted.
        CorruptedPDFError: If PDF structure is malformed.
    """
    if not os.path.isfile(pdf_path):
        raise EmptyPDFError("The file does not exist on disk.")

    size = os.path.getsize(pdf_path)
    if size == 0:
        raise EmptyPDFError("The uploaded file is empty (0 bytes).")

    # Check PDF magic bytes (%PDF-)
    with open(pdf_path, "rb") as f:
        header = f.read(5)
        if not header.startswith(b"%PDF-"):
            raise InvalidPDFError("The file header does not match standard PDF specification.")

    # Try opening with PyMuPDF
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise CorruptedPDFError(f"PDF document syntax is corrupted or unreadable: {str(exc)}")

    # Check password protection
    if doc.is_encrypted:
        doc.close()
        raise PasswordProtectedPDFError(
            "This statement is password-protected. Please remove the password before uploading."
        )

    # Check page count
    if len(doc) == 0:
        doc.close()
        raise EmptyPDFError("The PDF document contains 0 pages.")

    return doc
