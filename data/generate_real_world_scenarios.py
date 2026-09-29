"""Generate a set of synthetic PDF fixtures for real-world bank statement edge cases."""

from __future__ import annotations

import os

import fitz


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "scenarios")


def _write_pdf(path: str, lines: list[str], title: str = "Bank Statement") -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((40, 40), title, fontsize=16, fontname="helv", color=(0.0, 0.0, 0.0))
    y = 80
    for line in lines:
        page.insert_text((40, y), line, fontsize=10, fontname="helv")
        y += 18
    doc.save(path)
    doc.close()
    return path


def generate_all_scenarios() -> dict[str, str]:
    """Create synthetic PDFs covering the real-world edge cases required for E2E testing."""
    scenario_paths = {}

    scenario_paths["test_1_bank_a_text"] = _write_pdf(
        os.path.join(OUTPUT_DIR, "test_1_bank_a_text.pdf"),
        [
            "BANK A STATEMENT",
            "Date | Narration | Withdrawal | Deposit | Balance",
            "01/09/2026 | UPI-SWIGGY-1234 | 450.00 |  | 24,550.00",
            "02/09/2026 | SALARY CREDIT |  | 75,000.00 | 99,550.00",
        ],
        title="Bank A - Text Statement",
    )

    scenario_paths["test_2_bank_b_text"] = _write_pdf(
        os.path.join(OUTPUT_DIR, "test_2_bank_b_text.pdf"),
        [
            "BANK B STATEMENT",
            "Txn Date | Description | Debit | Credit | Closing Balance",
            "15-Oct-2025 | AMAZON INDIA ONLINE | ₹ 1,899.00 |  | 48,101.00",
            "16-Oct-2025 | SALARY CREDIT |  | 25,000.00 | 73,101.00",
        ],
        title="Bank B - Text Statement",
    )

    scenario_paths["test_3_scanned_statement"] = _write_pdf(
        os.path.join(OUTPUT_DIR, "test_3_scanned_statement.pdf"),
        [
            "SCANNED BANK STATEMENT",
            "Date Description Debit Credit Balance",
            "01/09/2026 UPI/AMAZON 1250.00 45000.00",
            "05/09/2026 SALARY CREDIT 50000.00 95000.00",
        ],
        title="Bank Statement - Scanned Copy",
    )

    scenario_paths["test_4_multi_page_statement"] = _write_pdf(
        os.path.join(OUTPUT_DIR, "test_4_multi_page_statement.pdf"),
        [
            "PAGE 1",
            "Date Description Debit Credit Balance",
            "01/09/2026 UPI SWIGGY 450.00 24500.00",
            "02/09/2026 DEPOSIT 75000.00 99500.00",
            "PAGE 2",
            "03/09/2026 ELECTRICITY BILL 2400.00 97100.00",
        ],
        title="Multi-page Statement",
    )

    scenario_paths["test_5_different_date_format"] = _write_pdf(
        os.path.join(OUTPUT_DIR, "test_5_different_date_format.pdf"),
        [
            "Date | Description | Debit | Credit | Balance",
            "01 Sep 2026 | UPI-SWIGGY | 450.00 |  | 24,550.00",
            "15-Oct-2025 | AMAZON INDIA | 1,899.00 |  | 48,101.00",
        ],
        title="Different Date Formats",
    )

    scenario_paths["test_6_different_amount_format"] = _write_pdf(
        os.path.join(OUTPUT_DIR, "test_6_different_amount_format.pdf"),
        [
            "Date | Description | Debit | Credit | Balance",
            "01/09/2026 | RENT PAYMENT | 1 234,56 |  | 88,765.44",
            "02/09/2026 | INTEREST CREDIT |  | ₹ 1,23,456.78 | 1,12,222.22",
        ],
        title="Different Amount Formats",
    )

    scenario_paths["test_7_multiline_description"] = _write_pdf(
        os.path.join(OUTPUT_DIR, "test_7_multiline_description.pdf"),
        [
            "Date | Description | Debit | Credit | Balance",
            "01/09/2026 | UPI\nPAYTM\nORDER 4201 | 450.00 |  | 24,550.00",
            "02/09/2026 | BANK\nTRANSFER\nEMPLOYEE |  | 8,000.00 | 32,550.00",
        ],
        title="Multi-line Description",
    )

    scenario_paths["test_8_missing_debit_credit"] = _write_pdf(
        os.path.join(OUTPUT_DIR, "test_8_missing_debit_credit.pdf"),
        [
            "Date | Description | Debit | Credit | Balance",
            "01/09/2026 | OPENING BALANCE |  |  | 50,000.00",
            "02/09/2026 | ACCOUNT UPDATE |  |  | 50,000.00",
        ],
        title="Missing Debit/Credit",
    )

    scenario_paths["test_9_duplicate_transaction"] = _write_pdf(
        os.path.join(OUTPUT_DIR, "test_9_duplicate_transaction.pdf"),
        [
            "Date | Description | Debit | Credit | Balance",
            "15/09/2026 | NETFLIX SUBSCRIPTION | 649.00 |  | 10,000.00",
            "15/09/2026 | NETFLIX SUBSCRIPTION | 649.00 |  | 9,351.00",
        ],
        title="Duplicate Transaction",
    )

    scenario_paths["test_10_balance_mismatch"] = _write_pdf(
        os.path.join(OUTPUT_DIR, "test_10_balance_mismatch.pdf"),
        [
            "Date | Description | Debit | Credit | Balance",
            "01/09/2026 | OPENING BAL |  | 10,000.00 | 10,000.00",
            "02/09/2026 | CLIENT PAYMENT |  | 2,000.00 | 12,000.00",
            "03/09/2026 | UTILITY BILL | 500.00 |  | 9,000.00",
        ],
        title="Balance Mismatch",
    )

    return scenario_paths


if __name__ == "__main__":
    generated = generate_all_scenarios()
    print("Generated scenario PDFs:")
    for name, path in generated.items():
        print(f"- {name}: {path}")
