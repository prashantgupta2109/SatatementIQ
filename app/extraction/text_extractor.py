"""Extract raw text from text-based PDF statements.

Handles page-level text extraction using pdfplumber.
Account detail extraction is delegated to account_extractor.
"""

import pdfplumber

from app.models import BankAccount
from app.extraction.account_extractor import extract_account_details


def extract_pages_text(pdf_path: str) -> list[str]:
    """Extract raw text from each page of a text-based PDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of text strings, one per page.
    """
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)

    return pages_text


def extract_account_info(pages_text: list[str]) -> BankAccount:
    """Extract account details from the first pages of a statement.

    Args:
        pages_text: List of text strings, one per page.

    Returns:
        Populated BankAccount dataclass.
    """
    # Account info is typically on the first 2 pages
    search_text = "\n".join(pages_text[:2])
    return extract_account_details(search_text)
