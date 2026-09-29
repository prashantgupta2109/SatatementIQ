"""Generate sample bank statement PDFs (text-based and image-based) for testing."""

import os
import fitz  # PyMuPDF


def generate_sample_statement(output_path: str = "data/sample_statement.pdf") -> str:
    """Generate a realistic text-based HDFC Bank statement PDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size

    # Header / Bank Title
    page.insert_text((50, 50), "HDFC BANK LIMITED", fontsize=16, fontname="helv", color=(0.1, 0.3, 0.6))
    page.insert_text((50, 70), "Retail Banking Branch, Bangalore", fontsize=10, fontname="helv", color=(0.4, 0.4, 0.4))

    # Account Details
    account_info = [
        "Account Holder Name: PRASHANT KUMAR",
        "A/C No.: 50100293847162",
        "IFSC Code: HDFC0001234",
        "Statement Period: 01/09/2026 to 30/09/2026",
    ]
    y = 110
    for line in account_info:
        page.insert_text((50, y), line, fontsize=10, fontname="helv")
        y += 18

    # Table Header Line
    y += 20
    page.draw_line(fitz.Point(50, y), fitz.Point(545, y), color=(0.2, 0.2, 0.2), width=1)
    y += 15

    # Table Column Headers
    headers = [
        (50, "Date"),
        (130, "Narration"),
        (330, "Withdrawal"),
        (410, "Deposit"),
        (480, "Balance"),
    ]
    for x, header in headers:
        page.insert_text((x, y), header, fontsize=10, fontname="helv", color=(0, 0, 0))

    y += 8
    page.draw_line(fitz.Point(50, y), fitz.Point(545, y), color=(0.6, 0.6, 0.6), width=0.5)
    y += 18

    # Transactions
    rows = [
        ("01/09/2026", "UPI/SWIGGY/ORDER_982", "450.00", "", "24,550.00"),
        ("02/09/2026", "SALARY CREDIT - TECH CORP", "", "75,000.00", "99,550.00"),
        ("05/09/2026", "AMAZON PAY RETAIL", "1,899.00", "", "97,651.00"),
        ("10/09/2026", "BESCOM ELECTRICITY BILL", "1,240.00", "", "96,411.00"),
        ("12/09/2026", "NETFLIX ENTERTAINMENT SUB", "649.00", "", "95,762.00"),
        ("15/09/2026", "ZERODHA BROKING MF SIP", "5,000.00", "", "90,762.00"),
        ("18/09/2026", "UBER RIDE TRIP BANGALORE", "320.00", "", "90,442.00"),
        ("20/09/2026", "ATM CASH WITHDRAWAL NFS", "2,000.00", "", "88,442.00"),
        ("25/09/2026", "APOLLO PHARMACY MEDS", "780.00", "", "87,662.00"),
        ("28/09/2026", "UPI/XYZ/MARKETPLACE", "1,250.00", "", "86,412.00"),
    ]

    for date_str, desc, wdl, dep, bal in rows:
        page.insert_text((50, y), date_str, fontsize=9, fontname="helv")
        page.insert_text((130, y), desc, fontsize=9, fontname="helv")
        if wdl:
            page.insert_text((330, y), wdl, fontsize=9, fontname="helv")
        if dep:
            page.insert_text((410, y), dep, fontsize=9, fontname="helv")
        page.insert_text((480, y), bal, fontsize=9, fontname="helv")
        y += 18

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    doc.close()
    return output_path


if __name__ == "__main__":
    path = generate_sample_statement()
    print(f"Generated sample statement at {path}")
