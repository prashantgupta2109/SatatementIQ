"""Unit tests for transaction_normalizer module."""

from datetime import date
import pandas as pd
import pytest

from app.models import Transaction, ValidationStatus, ClassificationMethod
from app.normalization.transaction_normalizer import (
    normalize_transactions,
    normalize_dataframe,
    transactions_to_dataframe,
)


class TestNormalizeTransactions:
    """Tests for normalize_transactions function."""

    def test_normalize_valid_raw_transactions(self):
        raw_txns = [
            Transaction(
                date="01/09/2026",
                description="  SWIGGY   BANGALORE  ",
                debit="₹450.50",
                credit=None,
                balance="25,000.00",
            ),
            Transaction(
                date="02-09-2026",
                description="SALARY CREDIT FROM ACME",
                debit=None,
                credit="75,000.00 CR",
                balance="1,00,000.00",
            ),
        ]

        normalized = normalize_transactions(raw_txns)

        assert len(normalized) == 2

        # Txn 1
        assert normalized[0].date == date(2026, 9, 1)
        assert normalized[0].description == "SWIGGY BANGALORE"
        assert normalized[0].debit == 450.50
        assert normalized[0].credit is None
        assert normalized[0].balance == 25000.00

        # Txn 2
        assert normalized[1].date == date(2026, 9, 2)
        assert normalized[1].description == "SALARY CREDIT FROM ACME"
        assert normalized[1].debit is None
        assert normalized[1].credit == 75000.00
        assert normalized[1].balance == 100000.00

    def test_skips_transactions_without_valid_date(self):
        """Header or summary rows without parseable dates should be excluded."""
        raw_txns = [
            Transaction(date="01/09/2026", description="Valid txn", debit="100.00"),
            Transaction(date="Page 1 of 3", description="Footer text", debit=None),
            Transaction(date="", description="Empty date row", debit="50.00"),
            Transaction(date=None, description="None date row", debit="20.00"),
        ]

        normalized = normalize_transactions(raw_txns)
        assert len(normalized) == 1
        assert normalized[0].description == "Valid txn"

    def test_dr_cr_detection_in_single_amount_column(self):
        """When an amount is placed in balance with Dr/Cr in description, split to debit/credit."""
        raw_txns = [
            Transaction(
                date="05/09/2026",
                description="ATM CASH WITHDRAWAL DR",
                debit=None,
                credit=None,
                balance="2000.00",
            ),
            Transaction(
                date="06/09/2026",
                description="DIVIDEND RECEIVED CR",
                debit=None,
                credit=None,
                balance="150.00",
            ),
        ]

        normalized = normalize_transactions(raw_txns)
        assert len(normalized) == 2

        # Dr -> debit
        assert normalized[0].debit == 2000.00
        assert normalized[0].credit is None
        assert normalized[0].balance is None

        # Cr -> credit
        assert normalized[1].credit == 150.00
        assert normalized[1].debit is None
        assert normalized[1].balance is None


class TestNormalizeDataFrame:
    """Tests for normalize_dataframe function (DataFrame to Transaction models)."""

    def test_normalize_raw_dataframe(self):
        df_raw = pd.DataFrame({
            "Txn Date": ["01/09/2026", "02/09/2026"],
            "Narration": ["AMAZON INDIA", "UBER RIDE"],
            "Withdrawal (Dr)": ["1,250.50", "340.00"],
            "Deposit (Cr)": ["", ""],
            "Closing Bal": ["20,000.00", "19,660.00"],
        })

        txns = normalize_dataframe(df_raw)
        assert len(txns) == 2

        assert txns[0].date == date(2026, 9, 1)
        assert txns[0].description == "AMAZON INDIA"
        assert txns[0].debit == 1250.50
        assert txns[0].credit is None
        assert txns[0].balance == 20000.00

        assert txns[1].date == date(2026, 9, 2)
        assert txns[1].description == "UBER RIDE"
        assert txns[1].debit == 340.00
        assert txns[1].balance == 19660.00


class TestTransactionsToDataFrame:
    """Tests for transactions_to_dataframe function."""

    def test_transactions_to_clean_dataframe(self):
        txns = [
            Transaction(
                date=date(2026, 9, 1),
                description="SWIGGY FOOD",
                debit=450.0,
                credit=None,
                balance=25000.0,
                category="Food & Dining",
                classification_method=ClassificationMethod.RULE_BASED,
                confidence=1.0,
                validation_status=ValidationStatus.VALID,
            )
        ]

        df = transactions_to_dataframe(txns)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["date"] == date(2026, 9, 1)
        assert df.iloc[0]["description"] == "SWIGGY FOOD"
        assert df.iloc[0]["debit"] == 450.0
        assert pd.isna(df.iloc[0]["credit"]) or df.iloc[0]["credit"] is None
        assert df.iloc[0]["category"] == "Food & Dining"
        assert df.iloc[0]["classification_method"] == "rule_based"
