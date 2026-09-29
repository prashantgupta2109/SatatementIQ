"""Unit tests for transaction and balance validation."""

from datetime import date
import pytest

from app.models import Transaction, ValidationStatus
from app.validation.balance_validator import validate_running_balances
from app.validation.transaction_validator import (
    validate_transaction_fields,
    detect_duplicates,
    validate_all_transactions,
)


class TestBalanceValidator:
    """Tests for running balance consistency validation."""

    def test_consistent_balance_calculation(self):
        """Prev: 10,000 | Credit: 2,000 | Debit: 500 => Expected: 11,500."""
        txns = [
            Transaction(date=date(2026, 9, 1), description="Opening", debit=None, credit=10000.0, balance=10000.0),
            Transaction(date=date(2026, 9, 2), description="Client Payment", debit=None, credit=2000.0, balance=12000.0),
            Transaction(date=date(2026, 9, 3), description="Utility Bill", debit=500.0, credit=None, balance=11500.0),
        ]

        validated = validate_running_balances(txns)

        for t in validated:
            assert t.validation_status == ValidationStatus.VALID
            assert len(t.validation_notes) == 0

    def test_inconsistent_balance_flags_warning_without_discarding(self):
        """When extracted balance does not match previous + credit - debit, mark WARNING."""
        txns = [
            Transaction(date=date(2026, 9, 1), description="Initial", debit=None, credit=10000.0, balance=10000.0),
            # Prev 10,000 + Credit 2,000 - Debit 500 = 11,500, but extracted says 9,000!
            Transaction(date=date(2026, 9, 2), description="Salary credit", debit=500.0, credit=2000.0, balance=9000.0),
        ]

        validated = validate_running_balances(txns)

        # The transaction must NOT be discarded
        assert len(validated) == 2
        # It must be marked as WARNING
        assert validated[1].validation_status == ValidationStatus.WARNING
        assert any("Balance inconsistency" in note for note in validated[1].validation_notes)


class TestTransactionValidator:
    """Tests for individual transaction field validation and duplicate detection."""

    def test_valid_transaction(self):
        txn = Transaction(
            date=date(2026, 9, 1),
            description="Swiggy Food Delivery",
            debit=450.0,
            credit=None,
            balance=25000.0,
        )
        status, notes = validate_transaction_fields(txn)
        assert status == ValidationStatus.VALID
        assert len(notes) == 0

    def test_missing_date(self):
        txn = Transaction(
            date=None,
            description="Something",
            debit=100.0,
        )
        status, notes = validate_transaction_fields(txn)
        assert status == ValidationStatus.INVALID
        assert any("Missing or unparseable" in n for n in notes)

    def test_empty_description(self):
        txn = Transaction(
            date=date(2026, 9, 1),
            description="",
            debit=100.0,
        )
        status, notes = validate_transaction_fields(txn)
        assert status == ValidationStatus.WARNING
        assert any("Missing transaction description" in n for n in notes)

    def test_missing_amounts(self):
        txn = Transaction(
            date=date(2026, 9, 1),
            description="Fee",
            debit=None,
            credit=None,
        )
        status, notes = validate_transaction_fields(txn)
        assert status == ValidationStatus.INVALID
        assert any("neither debit nor credit" in n for n in notes)

    def test_invalid_amount_validation_failure(self):
        """invalid amount → validation failure"""
        # Non-numeric string as debit amount
        txn_non_numeric = Transaction(
            date=date(2026, 9, 1),
            description="Payment with corrupt amount",
            debit="corrupt_amount",
            credit=None,
        )
        status, notes = validate_transaction_fields(txn_non_numeric)
        assert status == ValidationStatus.INVALID
        assert any("not numeric" in n for n in notes)

        # Neither debit nor credit present
        txn_no_amount = Transaction(
            date=date(2026, 9, 1),
            description="Missing amount",
            debit=None,
            credit=None,
        )
        status_none, notes_none = validate_transaction_fields(txn_no_amount)
        assert status_none == ValidationStatus.INVALID

    def test_duplicate_transactions_flagged_with_warning(self):
        txns = [
            Transaction(date=date(2026, 9, 1), description="Netflix Subscription", debit=649.0, balance=10000.0),
            Transaction(date=date(2026, 9, 1), description="Netflix Subscription", debit=649.0, balance=9351.0),
        ]

        validated = detect_duplicates(txns)
        assert len(validated) == 2
        assert validated[0].validation_status == ValidationStatus.WARNING
        assert validated[1].validation_status == ValidationStatus.WARNING
        assert any("duplicate" in n for n in validated[0].validation_notes)


class TestValidateAllTransactions:
    """End-to-end integration test of the validation pipeline."""

    def test_end_to_end_validation_preserves_all_records(self):
        txns = [
            Transaction(date=date(2026, 9, 1), description="Deposit", credit=10000.0, balance=10000.0),
            Transaction(date=date(2026, 9, 2), description="Withdrawal", debit=500.0, balance=9500.0),
            # Defective row: balance mismatch
            Transaction(date=date(2026, 9, 3), description="Store Purchase", debit=300.0, balance=8000.0),
        ]

        result = validate_all_transactions(txns)

        # Ensure no records are discarded
        assert len(result) == 3
        assert result[0].validation_status == ValidationStatus.VALID
        assert result[1].validation_status == ValidationStatus.VALID
        assert result[2].validation_status == ValidationStatus.WARNING
        assert len(result[2].validation_notes) > 0
