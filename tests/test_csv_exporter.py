"""Unit tests for CSV exporter module."""

import io
from datetime import date
import pandas as pd
import pytest

from app.models import Transaction, ClassificationMethod, ValidationStatus
from app.export.csv_exporter import (
    export_to_csv,
    export_to_csv_bytes,
    transactions_to_export_dataframe,
)


class TestCSVExporter:
    """Verifies schema, formatting, and file generation for CSV exports."""

    @pytest.fixture
    def sample_transactions(self):
        return [
            Transaction(
                date=date(2026, 9, 1),
                description="SWIGGY FOOD ORDER",
                debit=450.0,
                credit=None,
                balance=24550.0,
                category="Food & Dining",
                classification_method=ClassificationMethod.RULE_BASED,
                confidence=1.00,
                validation_status=ValidationStatus.VALID,
            ),
            Transaction(
                date=date(2026, 9, 2),
                description="AMAZON INDIA SHOPPING",
                debit=1899.50,
                credit=None,
                balance=22650.50,
                category="Shopping",
                classification_method=ClassificationMethod.ML_MODEL,
                confidence=0.87,
                validation_status=ValidationStatus.WARNING,
            ),
        ]

    def test_csv_exact_columns(self, sample_transactions):
        """Verifies exact column schema requested in Phase 16."""
        df = transactions_to_export_dataframe(sample_transactions)
        expected_columns = [
            "Date",
            "Description",
            "Debit",
            "Credit",
            "Balance",
            "Category",
            "Classification Method",
            "Confidence",
            "Validation Status",
        ]
        assert list(df.columns) == expected_columns

    def test_csv_formatting_values(self, sample_transactions):
        df = transactions_to_export_dataframe(sample_transactions)

        # Row 1
        assert df.iloc[0]["Date"] == "2026-09-01"
        assert df.iloc[0]["Description"] == "SWIGGY FOOD ORDER"
        assert df.iloc[0]["Debit"] == "450.00"
        assert df.iloc[0]["Credit"] == ""
        assert df.iloc[0]["Balance"] == "24550.00"
        assert df.iloc[0]["Category"] == "Food & Dining"
        assert df.iloc[0]["Classification Method"] == "Rule"
        assert df.iloc[0]["Confidence"] == "1.00"
        assert df.iloc[0]["Validation Status"] == "VALID"

        # Row 2
        assert df.iloc[1]["Classification Method"] == "ML"
        assert df.iloc[1]["Confidence"] == "0.87"
        assert df.iloc[1]["Validation Status"] == "WARNING"

    def test_export_to_csv_bytes(self, sample_transactions):
        csv_bytes = export_to_csv_bytes(sample_transactions)
        assert isinstance(csv_bytes, bytes)
        csv_text = csv_bytes.decode("utf-8")

        assert "Date,Description,Debit,Credit,Balance" in csv_text
        assert "SWIGGY FOOD ORDER" in csv_text
        assert "AMAZON INDIA SHOPPING" in csv_text

    def test_export_to_csv_file(self, tmp_path, sample_transactions):
        output_file = tmp_path / "transactions.csv"
        path = export_to_csv(sample_transactions, output_path=str(output_file))

        assert output_file.exists()
        loaded_df = pd.read_csv(output_file)
        assert len(loaded_df) == 2
        assert "Classification Method" in loaded_df.columns
