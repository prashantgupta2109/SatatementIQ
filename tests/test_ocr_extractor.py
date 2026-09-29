"""Unit and integration tests for ocr_extractor module."""

from datetime import date

import numpy as np
import cv2
import fitz
import pytest
from app.exceptions import BankStatementError
from app.extraction.ocr_extractor import (
    preprocess_image,
    parse_ocr_text_to_transactions,
)
from app.ingestion.image_converter import image_bytes_to_pdf
from app.models import Transaction
from app.normalization.transaction_normalizer import normalize_transactions
from app.validation.transaction_validator import validate_all_transactions


class TestImageUploadConversion:
    """Verify raster image uploads can be prepared for the scanned-PDF OCR path."""

    def test_webp_image_converts_to_single_page_pdf(self):
        image = np.full((120, 240, 3), 255, dtype=np.uint8)
        cv2.putText(image, "BANK STATEMENT", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        encoded, webp_bytes = cv2.imencode(".webp", image)
        assert encoded

        pdf_bytes = image_bytes_to_pdf(webp_bytes.tobytes())

        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            assert len(document) == 1
            assert len(document[0].get_images()) == 1

    def test_invalid_image_bytes_raise_user_facing_error(self):
        with pytest.raises(BankStatementError, match="could not be decoded"):
            image_bytes_to_pdf(b"not an image")


class TestOCRPreprocessing:
    """Verify OpenCV image preprocessing stages."""

    def test_preprocess_image_grayscale_and_binary(self):
        """Verify that preprocessing turns an image into a single-channel binary image."""
        # Create a synthetic 3-channel BGR image with simulated text/noise
        synthetic_img = np.ones((200, 600, 3), dtype=np.uint8) * 240
        # Draw some dark text-like bars
        cv2.putText(
            synthetic_img,
            "15/06/2025 UPI-SWIGGY 450.00 12000.00",
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (20, 20, 20),
            2,
        )

        processed = preprocess_image(synthetic_img)

        # Output should be single channel
        assert len(processed.shape) == 2
        # Values should be thresholded (0 or 255)
        unique_vals = set(np.unique(processed))
        assert unique_vals.issubset({0, 255})


class TestOCRTextToTransactions:
    """Verify parsing step: Correct OCR Text -> Correct Transactions."""

    def test_parse_clean_ocr_text(self):
        sample_ocr_output = [
            """
            HDFC BANK STATEMENT
            Account Number: 12345678901234
            Date Description Debit Credit Balance
            01/09/2026 UPI/AMAZON/ORDER 1250.00 45000.00
            05/09/2026 SALARY CREDIT 50000.00 95000.00
            10/09/2026 ELECTRICITY BILL 2300.50 92699.50
            """
        ]

        txns = parse_ocr_text_to_transactions(sample_ocr_output)

        assert len(txns) == 3

        # Transaction 1
        assert txns[0].description == "UPI/AMAZON/ORDER"
        assert txns[0].debit == 1250.0
        assert txns[0].balance == 45000.0

        # Transaction 2
        assert "SALARY CREDIT" in txns[1].description
        assert txns[1].debit == 50000.0 or txns[1].balance == 95000.0

        # Transaction 3
        assert "ELECTRICITY BILL" in txns[2].description

    def test_parse_yearless_us_dates_and_balance_inferred_deposit(self):
        sample_ocr_output = ["\n".join([
            "Statement Period: 06/01/2022 to 06/30/2022",
            "Account Summary",
            "06/01 Rent Bill 670.00 33,902.23",
            "06/03 Check No. 3456 740.00 34,642.23",
            "Payment from Nala Spencer",
            "06/08 Electric Bill 347.85 34,294.38",
            "06/13 Phone Bill 75.45 34,218.93",
            "06/15 Deposit 7,245.00 41,463.93",
            "06/18 Debit Transaction 339.96 41,123.97",
            "Photography Tools Warehouse",
            "06/24 Deposit 3,255.00 44,378.97",
            "06/25 Internet Bill 88.88 44,290.09",
            "06/28 Check No. 0231 935.00 45,225.09",
            "Payment from Kyubi Tayler",
            "06/29 Payroll Run 6,493.65 38,731.44",
            "06/30 Debit Transaction 1,234.98 37,496.46",
            "Picture Perfect Equipments",
            "06/30 Interest Earned 18.75 37,515.21",
            "06/30 Withholding Tax 3.75 37,511.46",
            "Ending Balance 37,511.46",
            "FINANCE STRATEGISTS",
        ])]

        transactions = parse_ocr_text_to_transactions(sample_ocr_output)

        assert len(transactions) == 13
        assert transactions[0].date == date(2022, 6, 1)
        assert transactions[0].debit == 670.0
        assert transactions[1].date == date(2022, 6, 3)
        assert transactions[1].credit == 740.0
        assert transactions[1].debit is None
        assert "Payment from Nala Spencer" in transactions[1].description
        assert "Photography Tools Warehouse" in transactions[5].description
        assert transactions[8].credit == 935.0
        assert "Payment from Kyubi Tayler" in transactions[8].description
        assert transactions[10].date == date(2022, 6, 30)
        assert transactions[12].description == "Withholding Tax"
        assert transactions[12].debit == 3.75

    def test_placeholder_dates_are_retained_with_review_flags(self):
        sample_ocr_output = ["\n".join([
            "STATEMENT OF ACCOUNT",
            "Period Covered: mm/dd/yyyy to mm/dd/yyyy",
            "Opening Balance: 175,800.00",
            "DATE DESCRIPTION CREDIT DEBIT BALANCE",
            "mm/dd/yyyy Payment - Credit Card 5,400.00 170,400.00",
            "mm/dd/yyyy Payment - Insurance 3,000.00 167,400.00",
            "mm/dd/yyyy Account Transfer In 500,000.00 667,400.00",
            "mm/dd/yyyy Cheque Deposit 10,000.00 677,400.00",
            "mm/dd/yyyy Payment - Electricity 1,500.00 675,900.00",
            "mm/dd/yyyy Payment - Water Utility 600.00 675,300.00",
            "mm/dd/yyyy Payment - Car Loan 3,500.00 671,800.00",
            "mm/dd/yyyy Account Transfer Out 80,000.00 591,800.00",
            "End of Transactions",
        ])]

        extracted = parse_ocr_text_to_transactions(sample_ocr_output)
        normalized = normalize_transactions(extracted)
        validated = validate_all_transactions(normalized)

        assert len(validated) == 8
        assert all(txn.date is None for txn in validated)
        assert all(txn.validation_status.value == "invalid" for txn in validated)
        assert all(txn.needs_review for txn in validated)
        assert validated[0].debit == 5400.0
        assert validated[0].credit is None
        assert validated[2].credit == 500000.0
        assert validated[2].debit is None
        assert validated[-1].description == "Account Transfer Out"
