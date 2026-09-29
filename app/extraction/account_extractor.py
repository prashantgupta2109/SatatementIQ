"""Extract account-level details from bank statement text.

Uses configurable field aliases so that variations like
"Account Number", "A/C No.", "A/C Number" all map to `account_number`.
"""

import re
from app.models import BankAccount


# ---------------------------------------------------------------------------
# Configurable aliases — add new variations here as needed
# ---------------------------------------------------------------------------

_FIELD_ALIASES: dict[str, list[str]] = {
    "account_number": [
        "Account Number",
        "Account No",
        "Account No.",
        "A/C No",
        "A/C No.",
        "A/C Number",
        "Acct No",
        "Acct Number",
        "Account #",
    ],
    "account_holder": [
        "Account Holder",
        "Account Name",
        "Customer Name",
        "Name of Account Holder",
        "Account Holder Name",
        "Name",
        "Client Name",
    ],
    "ifsc": [
        "IFSC Code",
        "IFSC",
        "IFS Code",
        "IFSC No",
    ],
    "statement_period": [
        "Statement Period",
        "Statement From",
        "Statement Date",
        "Statement for the period",
        "Period",
        "From Date",
    ],
}

# Known Indian bank names for detection
_KNOWN_BANKS = [
    "State Bank of India", "SBI",
    "HDFC Bank",
    "ICICI Bank",
    "Axis Bank",
    "Punjab National Bank", "PNB",
    "Bank of Baroda", "BOB",
    "Kotak Mahindra Bank",
    "Yes Bank",
    "IndusInd Bank",
    "Canara Bank",
    "Union Bank of India",
    "Bank of India", "BOI",
    "IDBI Bank",
    "Federal Bank",
    "RBL Bank",
    "South Indian Bank",
    "Bandhan Bank",
    "Indian Overseas Bank", "IOB",
    "Central Bank of India",
    "UCO Bank",
]

# Account number: 9-18 digits
_ACCT_NUM_PATTERN = re.compile(r"(\d{9,18})")

# IFSC: 4 uppercase letters + 0 + 6 alphanumeric
_IFSC_PATTERN = re.compile(r"([A-Z]{4}0[A-Z0-9]{6})")

# Date range: captures "dd/mm/yyyy to dd/mm/yyyy" style periods
_DATE_RANGE_PATTERN = re.compile(
    r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})"
    r"\s*(?:to|–|—|-|till)\s*"
    r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    re.IGNORECASE,
)


def extract_account_details(text: str) -> BankAccount:
    """Extract all account-level details from statement text.

    Args:
        text: Raw text from the first 1-2 pages of the statement.

    Returns:
        Populated BankAccount dataclass.
    """
    account = BankAccount()

    account.bank_name = _extract_bank_name(text)
    account.account_number = _extract_field(text, "account_number", _ACCT_NUM_PATTERN)
    account.ifsc = _extract_field(text, "ifsc", _IFSC_PATTERN)
    account.account_holder = _extract_holder_name(text)
    account.statement_period = _extract_period(text)

    return account


def _extract_field(text: str, field: str, value_pattern: re.Pattern) -> str | None:
    """Extract a field value by searching near its alias labels."""
    cleaned_text = text.replace("\u00a0", " ")

    for alias in _FIELD_ALIASES.get(field, []):
        pattern = re.compile(
            rf"{re.escape(alias)}\s*[:\-\s]*([A-Za-z0-9][A-Za-z0-9\s/.,\-]*)",
            re.IGNORECASE,
        )
        match = pattern.search(cleaned_text)
        if not match:
            continue

        candidate = match.group(1).strip()
        candidate = candidate.split("\n")[0].strip()
        candidate = re.sub(r"\s+", " ", candidate)

        if field == "ifsc":
            compact = re.sub(r"[^A-Z0-9]", "", candidate.upper())
            if re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", compact):
                return compact
            if re.fullmatch(r"[A-Z0-9]{11}", compact):
                return compact

        if field == "account_number":
            digits = re.sub(r"\D", "", candidate)
            if 9 <= len(digits) <= 18:
                return digits
            fallback = value_pattern.search(candidate)
            if fallback:
                return fallback.group(1).strip()

        if field in {"account_holder", "statement_period"}:
            value = candidate.strip(" :;,-")
            if value:
                return value

        # Generic fallback for other fields
        value_match = value_pattern.search(candidate)
        if value_match:
            return value_match.group(1).strip()

    if field == "ifsc":
        match = value_pattern.search(cleaned_text)
        if match:
            return match.group(1).strip()

    return None


def _extract_bank_name(text: str) -> str | None:
    """Detect bank name from known bank list."""
    # Sort by length descending so "State Bank of India" matches before "Bank of India"
    for bank in sorted(_KNOWN_BANKS, key=len, reverse=True):
        if re.search(re.escape(bank), text, re.IGNORECASE):
            return bank
    return None


def _extract_holder_name(text: str) -> str | None:
    """Extract account holder name using alias labels."""
    # Sort aliases longest-first to match "Account Holder Name" before "Name"
    aliases = sorted(_FIELD_ALIASES["account_holder"], key=len, reverse=True)
    for alias in aliases:
        escaped = re.escape(alias)
        pattern = re.compile(
            rf"{escaped}\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]+)",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            name = match.group(1).strip()
            # Clean up: stop at newline or next field
            name = name.split("\n")[0].strip()
            if len(name) >= 2:
                return name
    return None


def _extract_period(text: str) -> str | None:
    """Extract statement period as a date range string."""
    # First try: look near alias labels
    for alias in _FIELD_ALIASES["statement_period"]:
        escaped = re.escape(alias)
        pattern = re.compile(
            rf"{escaped}\s*[:\-\s]\s*(.+)",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            line = match.group(1).split("\n")[0].strip()
            # Try to find a date range within the matched line
            range_match = _DATE_RANGE_PATTERN.search(line)
            if range_match:
                return f"{range_match.group(1)} to {range_match.group(2)}"
            # Return the raw line if it looks like a period
            if len(line) >= 5:
                return line

    # Fallback: find any date range in the text
    range_match = _DATE_RANGE_PATTERN.search(text)
    if range_match:
        return f"{range_match.group(1)} to {range_match.group(2)}"

    return None
