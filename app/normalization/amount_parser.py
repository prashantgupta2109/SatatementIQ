"""Parse and clean monetary amounts from bank statements.

Handles Indian formatting quirks:
    - Comma separators: 1,23,456.78
    - Spaces within amounts: 1 234.56
    - Currency symbols: Rs., INR, ₹
    - Dr/Cr suffixes: 5,000.00 Dr → debit
    - Negative signs
    - Empty / dash values
"""

import re


# Currency prefixes to remove (order matters — longest first)
_CURRENCY_PREFIXES = re.compile(
    r"(?:Rs\.?|INR|₹|\$)\s*", re.IGNORECASE
)

# Detect Dr/Cr suffix
_DR_CR_PATTERN = re.compile(r"(Dr|Cr)\.?\s*$", re.IGNORECASE)


def parse_amount(value: str | float | int | None) -> float | None:
    """Parse a raw amount value into a float.

    Args:
        value: Raw amount string or numeric value.

    Returns:
        Parsed float, or None if the value is empty / zero / unparseable.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value) if value != 0 else None

    cleaned = str(value).strip()

    # Empty or dash means no value
    if not cleaned or cleaned in ("-", "--", "—", "nil", "NIL", "N/A"):
        return None

    # Remove currency symbols/prefixes
    cleaned = _CURRENCY_PREFIXES.sub("", cleaned).strip()

    # Remove Dr/Cr suffixes (handled separately by caller)
    cleaned = _DR_CR_PATTERN.sub("", cleaned).strip()

    # Handle negative signs
    is_negative = False
    if cleaned.startswith("-") or cleaned.startswith("("):
        is_negative = True
        cleaned = cleaned.strip("-()").strip()

    if not cleaned:
        return None

    cleaned = cleaned.replace(" ", "")

    # Normalize common international / Indian number formats:
    # - 1,23,456.78 -> 123456.78
    # - 1 234,56 -> 1234.56
    # - 1.234,56 -> 1234.56
    # - 1,234.56 -> 1234.56
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        if re.fullmatch(r"\d{1,3}(,\d{3})+", cleaned):
            cleaned = cleaned.replace(",", "")
        elif re.fullmatch(r"\d+(,\d{1,2})", cleaned):
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "." in cleaned and re.fullmatch(r"\d{1,3}(\.\d{3})+", cleaned):
        cleaned = cleaned.replace(".", "")

    if not cleaned:
        return None

    try:
        amount = float(cleaned)
        if is_negative:
            amount = -amount
        return amount if amount != 0 else None
    except ValueError:
        return None


def detect_dr_cr(value: str | None) -> str | None:
    """Detect if an amount string has a Dr or Cr suffix.

    Returns:
        "debit" if Dr suffix, "credit" if Cr suffix, None otherwise.
    """
    if not value or not isinstance(value, str):
        return None

    match = _DR_CR_PATTERN.search(value.strip())
    if match:
        suffix = match.group(1).lower()
        return "debit" if suffix == "dr" else "credit"

    return None


def clean_description(value: str | None) -> str:
    """Clean and normalize a transaction description.

    Args:
        value: Raw description text.

    Returns:
        Cleaned description string.
    """
    if not value:
        return ""

    text = str(value).strip()

    # Collapse newlines and repeated whitespace into single spaces
    text = re.sub(r"\s+", " ", text)

    # Remove common noise prefixes
    noise = ["BY TRANSFER-", "TO TRANSFER-", "BY CLG-", "TO CLG-"]
    for prefix in noise:
        if text.upper().startswith(prefix):
            text = text[len(prefix):].strip()

    return text
