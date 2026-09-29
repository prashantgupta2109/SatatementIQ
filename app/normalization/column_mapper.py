"""Map varying column names to the standard internal field names.

Banks use different headers for the same data. This module provides
a single lookup to normalize them all.

Standard fields: date | description | debit | credit | balance
"""


# Mapping: standard field name → list of known aliases (lowercase)
COLUMN_ALIASES: dict[str, list[str]] = {
    "date": [
        "date", "txn date", "transaction date", "value date",
        "posting date", "trans date", "txn dt", "value dt",
    ],
    "description": [
        "description", "narration", "particulars", "particular",
        "transaction details", "details", "remarks", "transaction description",
        "txn description", "narr", "trans particulars",
    ],
    "debit": [
        "debit", "withdrawal", "dr", "debit amount",
        "withdrawal amount", "debit(dr)", "dr.", "withdrawals",
        "amount debited", "debit (rs.)", "debit (inr)",
    ],
    "credit": [
        "credit", "deposit", "cr", "credit amount",
        "deposit amount", "credit(cr)", "cr.", "deposits",
        "amount credited", "credit (rs.)", "credit (inr)",
    ],
    "balance": [
        "balance", "closing balance", "running balance",
        "available balance", "bal", "balance (inr)", "balance (rs.)",
    ],
}

# Reverse lookup: alias → standard field name
_ALIAS_TO_STANDARD: dict[str, str] = {}
for field, aliases in COLUMN_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_STANDARD[alias] = field


def map_column(raw_name: str) -> str | None:
    """Map a raw column name to the standard field name.

    Args:
        raw_name: Column header as extracted from the PDF.

    Returns:
        Standard field name, or None if no match found.
    """
    cleaned = raw_name.strip().lower()

    # Direct match
    if cleaned in _ALIAS_TO_STANDARD:
        return _ALIAS_TO_STANDARD[cleaned]

    # Fuzzy: check if any alias is contained within the raw name
    for alias, field in _ALIAS_TO_STANDARD.items():
        if alias in cleaned:
            return field

    return None


def map_columns(raw_headers: list[str]) -> dict[str, str]:
    """Map a list of raw column headers to standard field names.

    Args:
        raw_headers: List of column headers from the PDF table.

    Returns:
        Dict mapping raw header → standard field name (only matched ones).
    """
    result = {}
    for header in raw_headers:
        if not header:
            continue
        standard = map_column(header)
        if standard:
            result[header] = standard
    return result
