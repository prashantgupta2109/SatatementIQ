"""Normalize date strings into Python date objects.

Handles the variety of date formats found across Indian bank statements:
    dd/mm/yyyy, dd-mm-yyyy, dd/mm/yy, dd MMM yyyy, yyyy-mm-dd, etc.
"""

from datetime import date, datetime


_DATE_FORMATS = [
    # Day first — most common in Indian statements
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d.%m.%y",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d.%m.%Y %H:%M:%S",
    # Day Month-name Year
    "%d %b %Y",
    "%d %b %y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%d/%b/%Y",
    "%d/%b/%y",
    "%d.%b.%Y",
    "%d.%b.%y",
    "%d %B %Y",
    "%d %B %y",
    "%d-%B-%Y",
    "%d-%B-%y",
    "%d/%B/%Y",
    "%d/%B/%y",
    "%d.%B.%Y",
    "%d.%B.%y",
    # ISO
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y.%m.%d %H:%M:%S",
]


def normalize_date(value: str | date | None) -> date | None:
    """Convert a date string to a Python date object.

    Args:
        value: Raw date string or already-parsed date.

    Returns:
        Normalized date, or None if parsing fails.
    """
    if value is None:
        return None

    if isinstance(value, date):
        return value

    cleaned = str(value).strip().strip(".,; ")
    if not cleaned:
        return None

    # Common bank-statement noise around dates (timestamps, trailing punctuation)
    candidates = [cleaned, cleaned.split("T")[0], cleaned.split()[0]]
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)

        for fmt in _DATE_FORMATS:
            try:
                parsed = datetime.strptime(candidate, fmt).date()
                # Sanity check: reject dates before 2000 or in the far future
                if parsed.year < 2000:
                    # Likely a 2-digit year that parsed wrong — try adding 2000
                    if parsed.year < 100:
                        parsed = parsed.replace(year=parsed.year + 2000)
                    else:
                        continue
                if parsed.year > datetime.now().year + 2:
                    continue
                return parsed
            except ValueError:
                continue

    return None
