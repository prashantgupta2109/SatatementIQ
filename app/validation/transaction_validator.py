"""Comprehensive transaction validator.

Validates extracted transactions against financial and data-integrity rules:
- Date validity (present, valid date object, realistic calendar year)
- Description validity (present, non-empty, meaningful text)
- Debit/Credit validity (valid non-negative numeric amounts, at least one present)
- Balance validity (valid numeric amount)
- Duplicate detection (flag potential duplicate entries with WARNING)
- Running balance consistency (via balance_validator)

Transactions with issues are marked with:
    validation_status = WARNING (or INVALID for severe structural defects)
and descriptive notes are attached to `validation_notes`. They are never silently discarded.
"""

from collections import Counter
from datetime import date
from typing import List, Tuple

from app.models import Transaction, ValidationStatus
from app.validation.balance_validator import validate_running_balances


def validate_transaction_fields(txn: Transaction) -> Tuple[ValidationStatus, List[str]]:
    """Validate field-level data integrity for a single transaction.

    Returns:
        Tuple of (ValidationStatus, list_of_notes)
    """
    notes: List[str] = []
    status = ValidationStatus.VALID

    # 1. Date check
    if txn.date is None:
        status = ValidationStatus.INVALID
        notes.append("Missing or unparseable transaction date")
    elif not isinstance(txn.date, date):
        status = ValidationStatus.INVALID
        notes.append(f"Invalid date type: {type(txn.date)}")
    elif txn.date.year < 2000 or txn.date.year > date.today().year + 2:
        status = ValidationStatus.WARNING
        notes.append(f"Unusual transaction year: {txn.date.year}")

    # 2. Description check
    desc = (txn.description or "").strip()
    if not desc:
        status = ValidationStatus.WARNING if status == ValidationStatus.VALID else status
        notes.append("Missing transaction description")
    elif len(desc) < 2:
        status = ValidationStatus.WARNING if status == ValidationStatus.VALID else status
        notes.append(f"Suspiciously short description: '{desc}'")

    # 3. Debit / Credit check
    has_debit = txn.debit is not None
    has_credit = txn.credit is not None

    if not has_debit and not has_credit:
        status = ValidationStatus.INVALID
        notes.append("Transaction has neither debit nor credit amount")
    else:
        if has_debit:
            if not isinstance(txn.debit, (int, float)):
                status = ValidationStatus.INVALID
                notes.append("Debit amount is not numeric")
            elif txn.debit < 0:
                status = ValidationStatus.WARNING
                notes.append(f"Negative debit amount detected: {txn.debit}")

        if has_credit:
            if not isinstance(txn.credit, (int, float)):
                status = ValidationStatus.INVALID
                notes.append("Credit amount is not numeric")
            elif txn.credit < 0:
                status = ValidationStatus.WARNING
                notes.append(f"Negative credit amount detected: {txn.credit}")

        if has_debit and has_credit and txn.debit > 0 and txn.credit > 0:
            status = ValidationStatus.WARNING
            notes.append("Both debit and credit amounts populated simultaneously")

    # 4. Balance check
    if txn.balance is not None and not isinstance(txn.balance, (int, float)):
        status = ValidationStatus.WARNING if status == ValidationStatus.VALID else status
        notes.append(f"Invalid non-numeric balance: {txn.balance}")

    return status, notes


def detect_duplicates(transactions: List[Transaction]) -> List[Transaction]:
    """Identify duplicate transactions based on identical date, amounts, and description.

    Flags potential duplicates with ValidationStatus.WARNING.
    """
    # Create key tuple: (date, debit, credit, description)
    keys = [
        (
            t.date,
            t.debit,
            t.credit,
            (t.description or "").strip().lower(),
        )
        for t in transactions
    ]
    counts = Counter(keys)

    for txn, key in zip(transactions, keys):
        if counts[key] > 1:
            if txn.validation_status != ValidationStatus.INVALID:
                txn.validation_status = ValidationStatus.WARNING
            note = f"Possible duplicate transaction (repeated {counts[key]} times)"
            if note not in txn.validation_notes:
                txn.validation_notes.append(note)

    return transactions


def validate_all_transactions(transactions: List[Transaction]) -> List[Transaction]:
    """Run full validation suite across all transactions in a statement:
    1. Field-level validity (date, description, amounts, balance)
    2. Duplicate detection
    3. Running balance continuity validation

    Returns:
        List of Transaction objects with updated validation_status and validation_notes.
    """
    if not transactions:
        return transactions

    # 1. Field-level checks
    for txn in transactions:
        field_status, notes = validate_transaction_fields(txn)
        if field_status != ValidationStatus.VALID:
            txn.validation_status = field_status
        for note in notes:
            if note not in txn.validation_notes:
                txn.validation_notes.append(note)

    # 2. Duplicate detection
    transactions = detect_duplicates(transactions)

    # 3. Running balance consistency check
    transactions = validate_running_balances(transactions)

    return transactions
