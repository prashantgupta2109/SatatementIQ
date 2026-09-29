"""Extract transaction tables from text-based PDF statements.

Pipeline:
    PDF → Pages → Tables → Rows → Raw transaction dicts

Uses pdfplumber's table extraction with fallback to line-by-line
parsing for statements that don't use visible table borders.
"""

import re
from datetime import datetime

import pdfplumber

from app.models import Transaction


# Common date formats in Indian bank statements
_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%d %b %Y", "%d %b %y", "%d-%b-%Y", "%d-%b-%y",
    "%Y-%m-%d",
]

# Regex to detect a date at the start of a line (transaction row indicator)
_DATE_PATTERN = re.compile(
    r"^\d{1,2}[\/\-\s](?:\d{1,2}|[A-Za-z]{3})[\/\-\s]\d{2,4}"
)

# Regex to extract amounts (handles commas and decimals)
_AMOUNT_PATTERN = re.compile(r"[\d,]+\.\d{2}")


def extract_transactions(pdf_path: str) -> list[Transaction]:
    """Extract transactions from a text-based PDF.

    Tries table extraction first, falls back to line parsing.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of Transaction objects with raw extracted data.
    """
    transactions = _extract_from_tables(pdf_path)

    if not transactions:
        transactions = _extract_from_lines(pdf_path)

    return transactions


def _extract_from_tables(pdf_path: str) -> list[Transaction]:
    """Extract transactions using pdfplumber's table detection."""
    transactions = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                header_row = _find_header_row(table)
                if header_row is None:
                    continue

                col_map = _map_columns(table[header_row])

                for row in table[header_row + 1:]:
                    txn = _parse_table_row(row, col_map)
                    if txn:
                        transactions.append(txn)

    return transactions


def _extract_from_lines(pdf_path: str) -> list[Transaction]:
    """Fallback: parse transactions line by line for borderless tables."""
    transactions = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = text.split("\n")

            for line in lines:
                line = line.strip()
                if not line or not _DATE_PATTERN.match(line):
                    continue

                txn = _parse_text_line(line)
                if txn:
                    transactions.append(txn)

    return transactions


def _find_header_row(table: list[list]) -> int | None:
    """Find the row index that contains column headers."""
    header_keywords = {"date", "description", "narration", "particular",
                       "debit", "credit", "withdrawal", "deposit",
                       "balance", "amount", "ref"}

    for i, row in enumerate(table):
        if not row:
            continue
        row_text = " ".join(str(cell).lower() for cell in row if cell)
        matches = sum(1 for kw in header_keywords if kw in row_text)
        if matches >= 2:
            return i

    return None


from app.normalization.column_mapper import map_column
from app.normalization.date_normalizer import normalize_date
from app.normalization.amount_parser import parse_amount, clean_description


def _map_columns(header_row: list) -> dict[str, int]:
    """Map column indices to their standard field names using column_mapper."""
    col_map = {}
    for i, cell in enumerate(header_row):
        if cell is None:
            continue
        cell_str = str(cell).strip()
        standard_name = map_column(cell_str)
        if standard_name and standard_name not in col_map:
            col_map[standard_name] = i

    return col_map


def _parse_table_row(row: list, col_map: dict[str, int]) -> Transaction | None:
    """Parse a single table row into a Transaction."""
    if not row or all(cell is None or str(cell).strip() == "" for cell in row):
        return None

    def get_cell(field: str) -> str:
        idx = col_map.get(field)
        if idx is not None and idx < len(row) and row[idx] is not None:
            return str(row[idx]).strip()
        return ""

    date_str = get_cell("date")
    if not date_str:
        return None

    parsed_date = normalize_date(date_str)
    if parsed_date is None:
        return None

    return Transaction(
        date=parsed_date,
        description=clean_description(get_cell("description")),
        debit=parse_amount(get_cell("debit")),
        credit=parse_amount(get_cell("credit")),
        balance=parse_amount(get_cell("balance")),
    )


def _parse_text_line(line: str) -> Transaction | None:
    """Parse a single text line into a Transaction."""
    # Extract date from the beginning
    date_match = _DATE_PATTERN.match(line)
    if not date_match:
        return None

    date_str = date_match.group(0)
    parsed_date = _parse_date(date_str)
    if parsed_date is None:
        return None

    remaining = line[date_match.end():].strip()

    # Extract all amounts from the line
    amounts = _AMOUNT_PATTERN.findall(remaining)
    amounts = [_parse_amount(a) for a in amounts]
    amounts = [a for a in amounts if a is not None]

    # Remove amounts from remaining to get description
    description = _AMOUNT_PATTERN.sub("", remaining).strip()
    description = re.sub(r"\s{2,}", " ", description)

    # Assign amounts based on count
    debit, credit, balance = None, None, None
    if len(amounts) == 3:
        debit, credit, balance = amounts
    elif len(amounts) == 2:
        # Check if description strongly suggests credit
        desc_lower = description.lower()
        credit_hints = ["credit", "deposit", "salary", "refund", "interest", " cr", "/cr"]
        if any(h in desc_lower for h in credit_hints):
            credit, balance = amounts[0], amounts[1]
        else:
            debit, balance = amounts[0], amounts[1]
    elif len(amounts) == 1:
        balance = amounts[0]

    return Transaction(
        date=parsed_date,
        description=description,
        debit=debit if debit and debit > 0 else None,
        credit=credit if credit and credit > 0 else None,
        balance=balance,
    )


def _parse_date(date_str: str) -> datetime | None:
    """Try multiple date formats and return the first match."""
    date_str = date_str.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(amount_str: str) -> float | None:
    """Parse an amount string like '1,234.56' into a float."""
    if not amount_str:
        return None
    cleaned = amount_str.replace(",", "").replace(" ", "").strip()
    try:
        value = float(cleaned)
        return value if value != 0 else None
    except ValueError:
        return None
