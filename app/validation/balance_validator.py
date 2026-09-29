"""Balance consistency validator for bank statement transactions.

Verifies mathematical consistency of running balances:
    Expected Balance = Previous Balance + Credit - Debit

If an extracted balance deviates from the mathematically expected balance:
    validation_status is set to ValidationStatus.WARNING
The transaction is flagged for inspection but NOT silently discarded.
"""

from typing import List, Optional
from app.models import Transaction, ValidationStatus


def validate_running_balances(
    transactions: List[Transaction],
    tolerance: float = 0.05,
) -> List[Transaction]:
    """Validate mathematical continuity of running balances across transactions.

    Formula:
        Expected Balance = Previous Balance + (Credit or 0.0) - (Debit or 0.0)

    If a mismatch occurs, flags the transaction with:
        validation_status = ValidationStatus.WARNING

    Args:
        transactions: List of Transaction objects (chronologically sorted preferred).
        tolerance: Maximum acceptable rounding discrepancy (default 0.05 currency units).

    Returns:
        The updated transactions list with validation notes and statuses.
    """
    if not transactions or len(transactions) < 2:
        return transactions

    # Determine sorting direction by dates if available
    is_reverse = False
    valid_dates = [t.date for t in transactions if t.date is not None]
    if len(valid_dates) >= 2 and valid_dates[0] > valid_dates[-1]:
        is_reverse = True

    # Work in chronological sequence (oldest to newest)
    indexed_txns = list(enumerate(transactions))
    if is_reverse:
        indexed_txns.reverse()

    prev_balance: Optional[float] = None

    for idx, txn in indexed_txns:
        current_balance = txn.balance
        debit = txn.debit or 0.0
        credit = txn.credit or 0.0

        if prev_balance is not None and current_balance is not None:
            expected_balance = prev_balance + credit - debit

            diff = abs(expected_balance - current_balance)
            if diff > tolerance:
                # Mark as warning, don't discard
                if txn.validation_status != ValidationStatus.INVALID:
                    txn.validation_status = ValidationStatus.WARNING

                note = (
                    f"Balance inconsistency: expected {expected_balance:,.2f} "
                    f"(prev {prev_balance:,.2f} + cr {credit:,.2f} - dr {debit:,.2f}), "
                    f"but extracted {current_balance:,.2f} (diff: {diff:,.2f})"
                )
                if note not in txn.validation_notes:
                    txn.validation_notes.append(note)

        # Update prev_balance for next iteration if current has a balance
        if current_balance is not None:
            prev_balance = current_balance

    return transactions
