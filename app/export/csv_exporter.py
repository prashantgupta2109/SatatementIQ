"""CSV Exporter for processed and classified bank transactions.

Exports transactions in standard structured CSV format with columns:
Date | Description | Debit | Credit | Balance | Category | Classification Method | Confidence | Validation Status
"""

import io
from typing import List, Optional
import pandas as pd

from app.models import Transaction, ClassificationMethod
from app.logging_config import get_logger

logger = get_logger("bank_processor")


def format_classification_method(method: ClassificationMethod) -> str:
    """Format ClassificationMethod enum into user-friendly title."""
    if method == ClassificationMethod.RULE_BASED:
        return "Rule"
    elif method == ClassificationMethod.ML_MODEL:
        return "ML"
    return "Unclassified"


def transactions_to_export_dataframe(transactions: List[Transaction]) -> pd.DataFrame:
    """Convert transactions to a DataFrame adhering to exact export column schema."""
    records = []
    for txn in transactions:
        records.append({
            "Date": txn.date.strftime("%Y-%m-%d") if txn.date else "",
            "Description": txn.description or "",
            "Debit": f"{txn.debit:.2f}" if txn.debit is not None else "",
            "Credit": f"{txn.credit:.2f}" if txn.credit is not None else "",
            "Balance": f"{txn.balance:.2f}" if txn.balance is not None else "",
            "Category": txn.category or "Uncategorized",
            "Classification Method": format_classification_method(txn.classification_method),
            "Confidence": f"{txn.confidence:.2f}",
            "Validation Status": txn.validation_status.value.upper(),
        })

    return pd.DataFrame(records)


def export_to_csv(
    transactions: List[Transaction],
    output_path: str = "transactions.csv",
) -> str:
    """Export transactions to a CSV file on disk.

    Args:
        transactions: List of processed Transaction objects.
        output_path: Target file path.

    Returns:
        The output path string.
    """
    df = transactions_to_export_dataframe(transactions)
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Export completed")
    return output_path


def export_to_csv_bytes(transactions: List[Transaction]) -> bytes:
    """Export transactions to CSV as UTF-8 encoded bytes for downloads.

    Args:
        transactions: List of processed Transaction objects.

    Returns:
        bytes representing CSV contents.
    """
    df = transactions_to_export_dataframe(transactions)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, encoding="utf-8")
    return buffer.getvalue().encode("utf-8")
