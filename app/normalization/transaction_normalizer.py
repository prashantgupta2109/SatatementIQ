"""Normalize raw extracted transactions into the standard format.

Takes raw transaction data (potentially with inconsistent column names,
varied date formats, messy amounts) and produces clean Transaction objects.

Final standard: date | description | debit | credit | balance
"""

import pandas as pd

from app.models import Transaction, ValidationStatus
from app.normalization.column_mapper import map_column
from app.normalization.date_normalizer import normalize_date
from app.normalization.amount_parser import (
    parse_amount,
    detect_dr_cr,
    clean_description,
)


def normalize_transactions(transactions: list[Transaction]) -> list[Transaction]:
    """Normalize a list of raw Transaction objects.

    Applies:
        - Date normalization
        - Amount parsing and cleaning
        - Description cleanup
        - Dr/Cr suffix handling
        - Debit/credit from single "amount" column detection

    Args:
        transactions: Raw Transaction objects from extraction.

    Returns:
        Cleaned and normalized Transaction objects.
    """
    normalized = []

    for txn in transactions:
        norm = Transaction(
            date=normalize_date(txn.date),
            description=clean_description(txn.description),
            debit=parse_amount(txn.debit),
            credit=parse_amount(txn.credit),
            balance=parse_amount(txn.balance),
            category=txn.category,
            classification_method=txn.classification_method,
            confidence=txn.confidence,
            needs_review=txn.needs_review,
            validation_status=txn.validation_status,
            validation_notes=list(txn.validation_notes),
        )

        # Handle Dr/Cr suffixes in description or single-amount rows
        dr_cr = detect_dr_cr(txn.description)
        if norm.debit is None and norm.credit is None and norm.balance is not None:
            desc_lower = (norm.description or "").lower()
            credit_keywords = [
                "salary", "credit", "deposit", "refund", "interest",
                "bonus", "reversal", "incoming", "cash in", "payroll",
            ]
            if dr_cr == "debit":
                norm.debit = norm.balance
                norm.balance = None
            elif dr_cr == "credit":
                norm.credit = norm.balance
                norm.balance = None
            elif any(keyword in desc_lower for keyword in credit_keywords):
                norm.credit = norm.balance
                norm.balance = None
            else:
                norm.debit = norm.balance
                norm.balance = None

        # Skip rows with no date (likely header/footer noise)
        if norm.date is None and norm.validation_status != ValidationStatus.INVALID:
            continue

        normalized.append(norm)

    return normalized


def normalize_dataframe(df: pd.DataFrame) -> list[Transaction]:
    """Normalize a raw DataFrame into Transaction objects.

    Handles column mapping, then applies all normalization rules.
    Useful when raw data comes as a DataFrame (e.g., from table extraction).

    Args:
        df: Raw DataFrame with potentially non-standard column names.

    Returns:
        List of normalized Transaction objects.
    """
    # Map columns to standard names
    rename_map = {}
    for col in df.columns:
        standard = map_column(str(col))
        if standard:
            rename_map[col] = standard

    df = df.rename(columns=rename_map)

    # Build Transaction objects from rows
    transactions = []
    for _, row in df.iterrows():
        txn = Transaction(
            date=row.get("date"),
            description=str(row.get("description", "")),
            debit=row.get("debit"),
            credit=row.get("credit"),
            balance=row.get("balance"),
        )
        transactions.append(txn)

    return normalize_transactions(transactions)


def transactions_to_dataframe(transactions: list[Transaction]) -> pd.DataFrame:
    """Convert normalized Transaction objects to a clean DataFrame.

    This is the standard output format:
        date | description | debit | credit | balance

    Args:
        transactions: List of normalized Transaction objects.

    Returns:
        Clean pandas DataFrame.
    """
    records = []
    for txn in transactions:
        records.append({
            "date": txn.date,
            "description": txn.description,
            "debit": txn.debit,
            "credit": txn.credit,
            "balance": txn.balance,
            "category": txn.category,
            "classification_method": txn.classification_method.value,
            "confidence": txn.confidence,
            "review_status": txn.review_status,
            "validation_status": txn.validation_status.value,
        })

    return pd.DataFrame(records)
