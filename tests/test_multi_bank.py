"""Tests for multi-bank statement table and column normalization.

Verifies that statements from Bank A, Bank B, Bank C, and various other
institutions are uniformly mapped to the internal standard:
date | description | debit | credit | balance
without requiring distinct application pipelines.
"""

from datetime import date
import pandas as pd
import pytest

from app.normalization.column_mapper import map_column, map_columns
from app.normalization.transaction_normalizer import normalize_dataframe, transactions_to_dataframe
from app.extraction.table_extractor import _map_columns, _parse_table_row


class TestMultiBankColumnMapping:
    """Verifies column headers from Bank A, Bank B, Bank C map to standard schema."""

    def test_bank_a_format(self):
        """Bank A: Date | Narration | Withdrawal | Deposit | Balance"""
        headers = ["Date", "Narration", "Withdrawal", "Deposit", "Balance"]
        mapped = [map_column(h) for h in headers]
        assert mapped == ["date", "description", "debit", "credit", "balance"]

    def test_bank_b_format(self):
        """Bank B: Txn Date | Description | Debit | Credit | Closing Balance"""
        headers = ["Txn Date", "Description", "Debit", "Credit", "Closing Balance"]
        mapped = [map_column(h) for h in headers]
        assert mapped == ["date", "description", "debit", "credit", "balance"]

    def test_bank_c_format(self):
        """Bank C: Transaction Date | Particulars | Dr | Cr | Balance"""
        headers = ["Transaction Date", "Particulars", "Dr", "Cr", "Balance"]
        mapped = [map_column(h) for h in headers]
        assert mapped == ["date", "description", "debit", "credit", "balance"]

    def test_additional_bank_variants(self):
        """Check additional real-world Indian bank variations."""
        headers = ["Value Date", "Transaction Details", "Withdrawal Amount", "Deposit Amount", "Available Balance"]
        mapped = [map_column(h) for h in headers]
        assert mapped == ["date", "description", "debit", "credit", "balance"]


class TestMultiBankDataFrameNormalization:
    """Verifies full DataFrame normalization across various bank layouts."""

    def test_bank_a_table_to_standard(self):
        raw_df = pd.DataFrame({
            "Date": ["01/09/2026", "02/09/2026"],
            "Narration": ["UPI-SWIGGY-1234", "SALARY CORP AC"],
            "Withdrawal": ["450.00", None],
            "Deposit": [None, "75,000.00"],
            "Balance": ["24,550.00", "99,550.00"],
        })

        txns = normalize_dataframe(raw_df)
        std_df = transactions_to_dataframe(txns)

        assert list(std_df["date"]) == [date(2026, 9, 1), date(2026, 9, 2)]
        assert list(std_df["description"]) == ["UPI-SWIGGY-1234", "SALARY CORP AC"]
        assert list(std_df["debit"]) == [450.0, None] or pd.isna(std_df["debit"].iloc[1])
        assert list(std_df["credit"])[1] == 75000.0
        assert list(std_df["balance"]) == [24550.0, 99550.0]

    def test_bank_b_table_to_standard(self):
        raw_df = pd.DataFrame({
            "Txn Date": ["15-Oct-2025"],
            "Description": ["AMAZON INDIA ONLINE"],
            "Debit": ["₹ 1,899.00"],
            "Credit": ["-"],
            "Closing Balance": ["48,101.00"],
        })

        txns = normalize_dataframe(raw_df)
        std_df = transactions_to_dataframe(txns)

        assert std_df.iloc[0]["date"] == date(2025, 10, 15)
        assert std_df.iloc[0]["description"] == "AMAZON INDIA ONLINE"
        assert std_df.iloc[0]["debit"] == 1899.0
        assert pd.isna(std_df.iloc[0]["credit"]) or std_df.iloc[0]["credit"] is None
        assert std_df.iloc[0]["balance"] == 48101.0

    def test_bank_c_table_to_standard(self):
        raw_df = pd.DataFrame({
            "Transaction Date": ["2026-03-31"],
            "Particulars": ["INTEREST CREDIT"],
            "Dr": [None],
            "Cr": ["1,245.50"],
            "Balance": ["1,50,000.00"],
        })

        txns = normalize_dataframe(raw_df)
        std_df = transactions_to_dataframe(txns)

        assert std_df.iloc[0]["date"] == date(2026, 3, 31)
        assert std_df.iloc[0]["description"] == "INTEREST CREDIT"
        assert pd.isna(std_df.iloc[0]["debit"]) or std_df.iloc[0]["debit"] is None
        assert std_df.iloc[0]["credit"] == 1245.50
        assert std_df.iloc[0]["balance"] == 150000.0
