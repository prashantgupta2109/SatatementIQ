"""Unit tests for date_normalizer module."""

import pytest
from datetime import date
from app.normalization.date_normalizer import normalize_date


class TestNormalizeDate:
    """Tests for normalize_date function."""

    # --- Required formats from assessment ---

    def test_dd_slash_mm_slash_yyyy(self):
        """01/09/2026 → 2026-09-01"""
        assert normalize_date("01/09/2026") == date(2026, 9, 1)

    def test_dd_dash_mm_dash_yyyy(self):
        """01-09-2026 → 2026-09-01"""
        assert normalize_date("01-09-2026") == date(2026, 9, 1)

    def test_dd_space_mmm_space_yyyy(self):
        """01 Sep 2026 → 2026-09-01"""
        assert normalize_date("01 Sep 2026") == date(2026, 9, 1)

    def test_dd_space_month_full_space_yyyy(self):
        """01 September 2026 → 2026-09-01"""
        assert normalize_date("01 September 2026") == date(2026, 9, 1)

    # --- Additional common formats ---

    def test_dd_dot_mm_dot_yyyy(self):
        assert normalize_date("15.03.2025") == date(2025, 3, 15)

    def test_dd_slash_mm_slash_yy(self):
        assert normalize_date("25/12/25") == date(2025, 12, 25)

    def test_dd_dash_mm_dash_yy(self):
        assert normalize_date("10-06-24") == date(2024, 6, 10)

    def test_dd_dot_mm_dot_yy(self):
        assert normalize_date("05.01.26") == date(2026, 1, 5)

    def test_dd_mmm_short_yy(self):
        assert normalize_date("15 Jan 24") == date(2024, 1, 15)

    def test_dd_dash_mmm_dash_yyyy(self):
        assert normalize_date("25-Mar-2025") == date(2025, 3, 25)

    def test_dd_dash_mmm_dash_yy(self):
        assert normalize_date("10-Jul-25") == date(2025, 7, 10)

    def test_dd_month_full_yy(self):
        assert normalize_date("01 January 26") == date(2026, 1, 1)

    def test_iso_format(self):
        assert normalize_date("2025-03-25") == date(2025, 3, 25)

    def test_iso_slash(self):
        assert normalize_date("2025/03/25") == date(2025, 3, 25)

    # --- Output is always YYYY-MM-DD ---

    def test_output_format_is_iso(self):
        """All outputs should produce date objects whose str is YYYY-MM-DD."""
        result = normalize_date("01/09/2026")
        assert str(result) == "2026-09-01"

    def test_output_format_dash_input(self):
        result = normalize_date("15-06-2025")
        assert str(result) == "2025-06-15"

    def test_output_format_month_name(self):
        result = normalize_date("20 March 2025")
        assert str(result) == "2025-03-20"

    # --- Pass-through for date objects ---

    def test_date_object_passthrough(self):
        d = date(2025, 6, 15)
        assert normalize_date(d) == d

    # --- Null / empty handling ---

    def test_none(self):
        assert normalize_date(None) is None

    def test_empty_string(self):
        assert normalize_date("") is None

    def test_whitespace(self):
        assert normalize_date("   ") is None

    def test_garbage(self):
        assert normalize_date("not-a-date") is None

    def test_incomplete_date(self):
        assert normalize_date("01/09") is None

    # --- Edge cases ---

    def test_leading_trailing_spaces(self):
        assert normalize_date("  01/09/2026  ") == date(2026, 9, 1)

    def test_end_of_month(self):
        assert normalize_date("31/01/2025") == date(2025, 1, 31)

    def test_leap_year(self):
        assert normalize_date("29/02/2024") == date(2024, 2, 29)

    def test_single_digit_day(self):
        assert normalize_date("1/09/2026") == date(2026, 9, 1)

    def test_single_digit_month(self):
        assert normalize_date("01/9/2026") == date(2026, 9, 1)
