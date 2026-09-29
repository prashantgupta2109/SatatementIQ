from datetime import date

from app.models import Transaction
from app.normalization.amount_parser import parse_amount
from app.normalization.date_normalizer import normalize_date
from app.normalization.transaction_normalizer import normalize_transactions
from app.validation.balance_validator import validate_running_balances
from app.validation.transaction_validator import detect_duplicates


def test_real_world_date_and_amount_variants():
    assert normalize_date("15-Oct-2025") == date(2025, 10, 15)
    assert normalize_date("01 Sep 2026") == date(2026, 9, 1)
    assert parse_amount("₹ 1,23,456.78") == 123456.78
    assert parse_amount("1 234,56") == 1234.56
    assert parse_amount("1.234,56") == 1234.56


def test_multiline_description_and_missing_debit_credit_are_normalized():
    txns = [
        Transaction(
            date="15-Oct-2025",
            description="UPI\nPAYTM\nORDER 4201",
            debit=None,
            credit=None,
            balance="1 245,80",
        ),
        Transaction(
            date="16-Oct-2025",
            description="SALARY CREDIT",
            debit=None,
            credit=None,
            balance="2 000,00",
        ),
    ]

    normalized = normalize_transactions(txns)

    assert normalized[0].description == "UPI PAYTM ORDER 4201"
    assert normalized[0].debit == 1245.80
    assert normalized[0].credit is None
    assert normalized[0].balance is None
    assert normalized[1].description == "SALARY CREDIT"
    assert normalized[1].credit == 2000.0


def test_duplicate_and_balance_mismatch_are_flagged():
    txns = [
        Transaction(date=date(2025, 10, 15), description="NETFLIX", debit=649.0, balance=9000.0),
        Transaction(date=date(2025, 10, 15), description="NETFLIX", debit=649.0, balance=8600.0),
        Transaction(date=date(2025, 10, 16), description="UPI PAYMENT", debit=200.0, credit=None, balance=8200.0),
    ]

    flagged = detect_duplicates(txns)
    assert any("duplicate" in note.lower() for note in flagged[0].validation_notes)

    validated = validate_running_balances(flagged)
    assert validated[2].validation_status.value == "warning"
    assert any("Balance inconsistency" in note for note in validated[2].validation_notes)
