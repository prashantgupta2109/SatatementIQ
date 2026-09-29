"""Unit tests for amount_parser module."""

import pytest
from app.normalization.amount_parser import parse_amount, detect_dr_cr, clean_description


# -----------------------------------------------------------------------
# parse_amount tests
# -----------------------------------------------------------------------

class TestParseAmount:
    """Tests for parse_amount function."""

    # --- Standard formats ---

    def test_plain_integer(self):
        assert parse_amount("1250") == 1250.0

    def test_plain_decimal(self):
        assert parse_amount("1250.50") == 1250.5

    def test_comma_separated(self):
        assert parse_amount("1,250.00") == 1250.0

    def test_indian_comma_format(self):
        assert parse_amount("1,23,456.78") == 123456.78

    def test_large_amount(self):
        assert parse_amount("10,00,000.00") == 1000000.0

    # --- Currency symbols ---

    def test_rupee_symbol(self):
        """₹1,250.50 → 1250.50"""
        assert parse_amount("₹1,250.50") == 1250.50
        assert parse_amount("\u20b91,250.50") == 1250.50

    def test_rs_prefix(self):
        assert parse_amount("Rs. 5,000.00") == 5000.0

    def test_rs_no_dot(self):
        assert parse_amount("Rs 5000") == 5000.0

    def test_inr_prefix(self):
        assert parse_amount("INR 2,500.75") == 2500.75

    def test_dollar_prefix(self):
        assert parse_amount("$100.00") == 100.0

    # --- Dr/Cr suffixes ---

    def test_dr_suffix(self):
        assert parse_amount("1,250.00 DR") == 1250.0

    def test_cr_suffix(self):
        assert parse_amount("1,250.00 CR") == 1250.0

    def test_dr_with_dot(self):
        assert parse_amount("500.00 Dr.") == 500.0

    def test_cr_with_dot(self):
        assert parse_amount("750.00 Cr.") == 750.0

    # --- Negative amounts ---

    def test_negative_sign(self):
        assert parse_amount("-1250") == -1250.0

    def test_negative_with_decimal(self):
        assert parse_amount("-1,250.50") == -1250.5

    def test_parentheses_negative(self):
        assert parse_amount("(1250.00)") == -1250.0

    # --- Empty / null values ---

    def test_none(self):
        assert parse_amount(None) is None

    def test_empty_string(self):
        assert parse_amount("") is None

    def test_dash(self):
        assert parse_amount("-") is None

    def test_double_dash(self):
        assert parse_amount("--") is None

    def test_em_dash(self):
        assert parse_amount("\u2014") is None

    def test_nil(self):
        assert parse_amount("NIL") is None

    def test_nil_lowercase(self):
        assert parse_amount("nil") is None

    def test_na(self):
        assert parse_amount("N/A") is None

    # --- Numeric inputs (int/float pass-through) ---

    def test_int_input(self):
        assert parse_amount(1250) == 1250.0

    def test_float_input(self):
        assert parse_amount(1250.50) == 1250.5

    def test_zero_int(self):
        assert parse_amount(0) is None

    def test_zero_float(self):
        assert parse_amount(0.0) is None

    # --- Edge cases ---

    def test_whitespace_only(self):
        assert parse_amount("   ") is None

    def test_amount_with_spaces(self):
        assert parse_amount("  1,250.00  ") == 1250.0

    def test_currency_with_spaces(self):
        assert parse_amount("Rs.  5,000.00") == 5000.0


# -----------------------------------------------------------------------
# detect_dr_cr tests
# -----------------------------------------------------------------------

class TestDetectDrCr:
    """Tests for detect_dr_cr function."""

    def test_dr_uppercase(self):
        assert detect_dr_cr("5,000.00 DR") == "debit"

    def test_cr_uppercase(self):
        assert detect_dr_cr("5,000.00 CR") == "credit"

    def test_dr_mixed_case(self):
        assert detect_dr_cr("5,000.00 Dr") == "debit"

    def test_cr_mixed_case(self):
        assert detect_dr_cr("5,000.00 Cr") == "credit"

    def test_dr_with_dot(self):
        assert detect_dr_cr("500.00 Dr.") == "debit"

    def test_cr_with_dot(self):
        assert detect_dr_cr("500.00 Cr.") == "credit"

    def test_no_suffix(self):
        assert detect_dr_cr("5000.00") is None

    def test_none_input(self):
        assert detect_dr_cr(None) is None

    def test_empty_string(self):
        assert detect_dr_cr("") is None

    def test_numeric_input(self):
        assert detect_dr_cr(12345) is None


# -----------------------------------------------------------------------
# clean_description tests
# -----------------------------------------------------------------------

class TestCleanDescription:
    """Tests for clean_description function."""

    def test_strips_whitespace(self):
        assert clean_description("  UPI-SWIGGY  ") == "UPI-SWIGGY"

    def test_collapses_spaces(self):
        assert clean_description("UPI   PAYMENT   SWIGGY") == "UPI PAYMENT SWIGGY"

    def test_removes_transfer_prefix(self):
        assert clean_description("BY TRANSFER-NEFT/12345") == "NEFT/12345"

    def test_removes_clg_prefix(self):
        assert clean_description("BY CLG-CHEQUE 987654") == "CHEQUE 987654"

    def test_none_input(self):
        assert clean_description(None) == ""

    def test_empty_string(self):
        assert clean_description("") == ""

    def test_normal_description(self):
        assert clean_description("NEFT-SALARY CREDIT") == "NEFT-SALARY CREDIT"
