"""OCR Extractor for scanned / image-based PDF bank statements.

Pipeline:
    Scanned PDF
         ↓
    PDF page → image (PyMuPDF)
         ↓
    OpenCV preprocessing:
         - Grayscale conversion
         - Thresholding (Otsu binarization)
         - Noise removal (morphology / median filter)
         ↓
    Tesseract OCR (pytesseract)
         ↓
    Text
         ↓
    Transaction parsing (via table/line extraction)
"""

import os
import re
import shutil
from datetime import date
from typing import List, Optional
import cv2
import fitz  # PyMuPDF
import numpy as np
import pytesseract

from app.models import Transaction, BankAccount, ValidationStatus
from app.extraction.account_extractor import extract_account_details
from app.extraction.table_extractor import _parse_text_line


_YEARLESS_DATE_PATTERN = re.compile(r"^\s*(\d{1,2})[/-](\d{1,2})(?:\s+|$)(.*)$")
_STATEMENT_PERIOD_YEAR_PATTERN = re.compile(
    r"(?:statement\s+period|period)\s*:?[^\n]{0,80}?\b((?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_FULL_NUMERIC_DATE_PATTERN = re.compile(r"\b(\d{1,2})/(\d{1,2})/((?:19|20)\d{2})\b")
_PLACEHOLDER_DATE_PATTERN = re.compile(
    r"^\s*(?:mm\s*/\s*dd\s*/\s*yyyy|dd\s*/\s*mm\s*/\s*yyyy)(?:\s+|$)(.*)$",
    re.IGNORECASE,
)
_OPENING_BALANCE_PATTERN = re.compile(
    r"\bopening\s+balance\b\s*:?\s*\$?\s*([\d,]+(?:\.\d{2})?)",
    re.IGNORECASE,
)


def _configure_tesseract_cmd():
    """Locate and configure the Tesseract executable path if not in system PATH."""
    if shutil.which("tesseract"):
        return

    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for path in common_paths:
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return


_configure_tesseract_cmd()


def pdf_page_to_image(page: fitz.Page, dpi: int = 300) -> np.ndarray:
    """Render a PyMuPDF PDF page into an OpenCV-compatible image (BGR).

    Args:
        page: PyMuPDF Page object.
        dpi: Target resolution for rendering (300 DPI is optimal for OCR).

    Returns:
        np.ndarray image in BGR format.
    """
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    # Convert buffer to numpy array
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 3:
        # RGB to BGR for OpenCV
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    elif pix.n == 1:
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
    else:
        img_bgr = img_array
    return img_bgr


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """Preprocess image using OpenCV to optimize OCR accuracy.

    Steps:
        1. Grayscale conversion
        2. Denoising / blur filter
        3. Otsu thresholding / binarization
        4. Morphological noise removal

    Args:
        image: Source image (BGR or Gray).

    Returns:
        Cleaned, high-contrast binary image.
    """
    # 1. Grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 2. Slight Gaussian blur to reduce high-frequency scan noise
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # 3. Thresholding (Otsu automatic thresholding)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 4. Morphological noise removal (opening removes isolated salt noise)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    return cleaned


def is_tesseract_available() -> bool:
    """Check if Tesseract binary is installed and discoverable."""
    _configure_tesseract_cmd()
    if shutil.which("tesseract"):
        return True
    if hasattr(pytesseract.pytesseract, "tesseract_cmd") and os.path.isfile(pytesseract.pytesseract.tesseract_cmd):
        return True
    return False


def ocr_image_to_text(image: np.ndarray, psm: int = 6) -> str:
    """Extract raw text from an image using Tesseract OCR.

    Args:
        image: Preprocessed or raw image.
        psm: Page segmentation mode (default 6: Assume a single uniform block of text).

    Returns:
        Extracted text string.
    """
    _configure_tesseract_cmd()
    if not is_tesseract_available():
        raise RuntimeError(
            "Tesseract OCR is not installed or not found on system PATH. "
            "Please install Tesseract-OCR to process scanned / image-based PDFs."
        )
    custom_config = f"--oem 3 --psm {psm}"
    text = pytesseract.image_to_string(image, config=custom_config)
    return text


def extract_text_from_scanned_pdf(pdf_path: str, dpi: int = 300) -> List[str]:
    """Convert each page of a scanned PDF to an image, preprocess, and OCR to text.

    Args:
        pdf_path: Path to the scanned PDF.
        dpi: Rendering DPI.

    Returns:
        List of extracted text strings, one per page.
    """
    pages_text: List[str] = []
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        raw_img = pdf_page_to_image(page, dpi=dpi)
        processed_img = preprocess_image(raw_img)
        page_text = ocr_image_to_text(processed_img)
        pages_text.append(page_text)

    doc.close()
    return pages_text


def parse_ocr_text_to_transactions(pages_text: List[str]) -> List[Transaction]:
    """Parse raw OCR text into Transaction models.

    Args:
        pages_text: List of OCR text strings per page.

    Returns:
        List of Transaction objects parsed from the lines.
    """
    transactions: List[Transaction] = []
    combined_text = "\n".join(pages_text)
    year_match = _STATEMENT_PERIOD_YEAR_PATTERN.search(combined_text)
    if year_match is None:
        year_match = re.search(r"\b((?:19|20)\d{2})\b", combined_text)
    statement_year = int(year_match.group(1)) if year_match else None
    opening_balance_match = _OPENING_BALANCE_PATTERN.search(combined_text)
    opening_balance = (
        float(opening_balance_match.group(1).replace(",", ""))
        if opening_balance_match
        else None
    )

    month_first = False
    for month_or_day, day_or_month, _ in _FULL_NUMERIC_DATE_PATTERN.findall(combined_text):
        first, second = int(month_or_day), int(day_or_month)
        if second > 12 and first <= 12:
            month_first = True
            break
        if first > 12 and second <= 12:
            break

    for text in pages_text:
        last_transaction: Optional[Transaction] = None
        lines = text.split("\n")
        for line in lines:
            line_cleaned = line.strip()
            if not line_cleaned:
                continue

            txn = _parse_text_line(line_cleaned)
            if txn is None and statement_year is not None:
                txn = _parse_yearless_date_line(line_cleaned, statement_year, month_first)
            if txn is None:
                txn = _parse_placeholder_date_line(line_cleaned)

            if txn:
                previous_balance = transactions[-1].balance if transactions else opening_balance
                _infer_amount_direction(txn, previous_balance)
                transactions.append(txn)
                last_transaction = txn
            elif _is_statement_footer(line_cleaned):
                last_transaction = None
            elif last_transaction is not None and _is_description_continuation(line_cleaned):
                last_transaction.description = " ".join(
                    part for part in (last_transaction.description, line_cleaned) if part
                )

    return transactions


def _parse_yearless_date_line(line: str, year: int, month_first: bool) -> Optional[Transaction]:
    """Parse MM/DD or DD/MM OCR rows using the statement's year and date order."""
    match = _YEARLESS_DATE_PATTERN.match(line)
    if match is None:
        return None

    first, second = int(match.group(1)), int(match.group(2))
    if first > 12 and second <= 12:
        day, month = first, second
    elif second > 12 and first <= 12:
        month, day = first, second
    elif month_first:
        month, day = first, second
    else:
        day, month = first, second

    try:
        row_date = date(year, month, day)
    except ValueError:
        return None

    day_first_date = f"{day:02d}/{month:02d}/{year}"
    txn = _parse_text_line(f"{day_first_date} {match.group(3)}")
    if txn is not None:
        txn.date = row_date
    return txn


def _parse_placeholder_date_line(line: str) -> Optional[Transaction]:
    """Keep financial rows whose date field is an unfilled date-format placeholder."""
    match = _PLACEHOLDER_DATE_PATTERN.match(line)
    if match is None:
        return None

    row_text = match.group(1)
    if len(re.findall(r"[\d,]+\.\d{2}", row_text)) < 2:
        return None

    txn = _parse_text_line(f"01/01/2000 {row_text}")
    if txn is None:
        return None

    txn.date = None
    txn.validation_status = ValidationStatus.INVALID
    txn.needs_review = True
    txn.validation_notes.append(
        "Transaction date is a template placeholder and was not provided."
    )
    return txn


def _infer_amount_direction(txn: Transaction, previous_balance: Optional[float]) -> None:
    """Use balance continuity to resolve ambiguous debit/credit OCR rows."""
    if previous_balance is None or txn.balance is None:
        return

    amount = txn.debit if txn.debit is not None else txn.credit
    if amount is None:
        return

    balance_change = txn.balance - previous_balance
    if abs(balance_change - amount) <= 0.05:
        txn.credit = amount
        txn.debit = None
    elif abs(balance_change + amount) <= 0.05:
        txn.debit = amount
        txn.credit = None


def _is_description_continuation(line: str) -> bool:
    """Identify wrapped narration lines without appending common statement totals."""
    if re.search(r"\d", line):
        return False

    lowered = line.lower()
    ignored_prefixes = (
        "account summary",
        "balance on ",
        "total money ",
        "ending balance",
        "statement period",
        "date description",
        "withdrawal deposit",
    )
    return not lowered.startswith(ignored_prefixes)


def _is_statement_footer(line: str) -> bool:
    """Stop joining OCR text to a transaction after statement totals begin."""
    lowered = line.lower().strip()
    return lowered.startswith((
        "ending balance",
        "end of statement",
        "end of transaction",
        "closing balance",
    ))


def extract_from_scanned_pdf(pdf_path: str) -> tuple[BankAccount, List[Transaction]]:
    """Complete extraction pipeline for scanned PDFs.

    Args:
        pdf_path: Path to scanned PDF.

    Returns:
        Tuple of (BankAccount, List[Transaction])
    """
    pages_text = extract_text_from_scanned_pdf(pdf_path)
    combined_header_text = "\n".join(pages_text[:2])
    account = extract_account_details(combined_header_text)
    transactions = parse_ocr_text_to_transactions(pages_text)

    return account, transactions
