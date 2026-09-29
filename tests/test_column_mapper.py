"""Unit tests for column_mapper module."""

import pytest
from app.normalization.column_mapper import (
    COLUMN_ALIASES,
    map_column,
    map_columns,
)


class TestColumnMapper:
    """Tests for mapping varying bank statement header aliases to standard names."""

    # --- Date column mapping ---

    @pytest.mark.parametrize(
        "header",
        [
            "date",
            "Date",
            "DATE",
            "txn date",
            "Txn Date",
            "transaction date",
            "Transaction Date",
            "value date",
            "Value Date",
            "posting date",
            "trans date",
            "txn dt",
            "value dt",
        ],
    )
    def test_date_column_variations(self, header):
        assert map_column(header) == "date"

    # --- Description column mapping ---

    @pytest.mark.parametrize(
        "header",
        [
            "description",
            "Description",
            "narration",
            "Narration",
            "particulars",
            "Particulars",
            "transaction details",
            "Transaction Details",
            "details",
            "remarks",
            "transaction description",
            "txn description",
            "narr",
            "trans particulars",
        ],
    )
    def test_description_column_variations(self, header):
        assert map_column(header) == "description"

    # --- Debit column mapping ---

    @pytest.mark.parametrize(
        "header",
        [
            "debit",
            "Debit",
            "DEBIT",
            "withdrawal",
            "Withdrawal",
            "dr",
            "DR",
            "dr.",
            "debit amount",
            "Debit Amount",
            "withdrawal amount",
            "debit(dr)",
            "withdrawals",
            "amount debited",
            "debit (rs.)",
            "debit (inr)",
        ],
    )
    def test_debit_column_variations(self, header):
        assert map_column(header) == "debit"

    # --- Credit column mapping ---

    @pytest.mark.parametrize(
        "header",
        [
            "credit",
            "Credit",
            "CREDIT",
            "deposit",
            "Deposit",
            "cr",
            "CR",
            "cr.",
            "credit amount",
            "Credit Amount",
            "deposit amount",
            "credit(cr)",
            "deposits",
            "amount credited",
            "credit (rs.)",
            "credit (inr)",
        ],
    )
    def test_credit_column_variations(self, header):
        assert map_column(header) == "credit"

    # --- Balance column mapping ---

    @pytest.mark.parametrize(
        "header",
        [
            "balance",
            "Balance",
            "BALANCE",
            "closing balance",
            "Closing Balance",
            "running balance",
            "available balance",
            "bal",
            "balance (inr)",
            "balance (rs.)",
        ],
    )
    def test_balance_column_variations(self, header):
        assert map_column(header) == "balance"

    # --- Whitespace and case-sensitivity ---

    def test_header_with_extra_spaces(self):
        assert map_column("  Txn Date  ") == "date"
        assert map_column("  Withdrawal Amount  ") == "debit"
        assert map_column("  Deposit Amount  ") == "credit"
        assert map_column("  Closing Balance  ") == "balance"

    def test_unrecognized_column_returns_none(self):
        assert map_column("Chq No") is None
        assert map_column("Reference No") is None
        assert map_column("Unknown Header") is None
        assert map_column("") is None


class TestMapColumnsBatch:
    """Tests for map_columns function (batch dictionary mapping)."""

    def test_map_standard_headers(self):
        headers = ["Txn Date", "Narration", "Withdrawal (Dr)", "Deposit (Cr)", "Closing Bal"]
        expected = {
            "Txn Date": "date",
            "Narration": "description",
            "Withdrawal (Dr)": "debit",
            "Deposit (Cr)": "credit",
            "Closing Bal": "balance",
        }
        result = map_columns(headers)
        assert result == expected

    def test_map_columns_ignores_unmapped(self):
        headers = ["Txn Date", "Chq No", "Narration", "Ref ID", "Debit", "Credit", "Balance"]
        result = map_columns(headers)
        assert "Chq No" not in result
        assert "Ref ID" not in result
        assert result["Txn Date"] == "date"
        assert result["Narration"] == "description"
        assert result["Debit"] == "debit"
        assert result["Credit"] == "credit"
        assert result["Balance"] == "balance"

    def test_map_columns_empty_list(self):
        assert map_columns([]) == {}
