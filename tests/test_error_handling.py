"""Unit tests for error handling and PDF pre-flight validation."""

import os
import fitz  # PyMuPDF
import pytest

from app.exceptions import (
    BankStatementError,
    InvalidPDFError,
    PasswordProtectedPDFError,
    EmptyPDFError,
    CorruptedPDFError,
    NoTransactionsFoundError,
)
from app.ingestion.pdf_validator import validate_pdf_file
from app.extraction.table_extractor import extract_transactions


class TestPDFErrorHandling:
    """Verifies that invalid, corrupted, encrypted, or empty PDFs raise clear domain exceptions."""

    def test_empty_zero_byte_pdf(self, tmp_path):
        empty_file = tmp_path / "empty.pdf"
        empty_file.write_bytes(b"")

        with pytest.raises(EmptyPDFError) as exc_info:
            validate_pdf_file(str(empty_file))

        assert "empty" in exc_info.value.reason.lower()
        assert issubclass(EmptyPDFError, BankStatementError)

    def test_invalid_non_pdf_file(self, tmp_path):
        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_text("Hello, this is not a PDF at all!")

        with pytest.raises(InvalidPDFError) as exc_info:
            validate_pdf_file(str(fake_pdf))

        assert "header" in exc_info.value.reason.lower() or "not a valid" in exc_info.value.reason.lower()

    def test_corrupted_pdf_file(self, tmp_path):
        corrupt_file = tmp_path / "corrupt.pdf"
        # Has %PDF- magic bytes but broken structure
        corrupt_file.write_bytes(b"%PDF-1.4\n%%EOF\nGARBAGE_BYTES_CORRUPTED_STREAM")

        with pytest.raises(CorruptedPDFError) as exc_info:
            validate_pdf_file(str(corrupt_file))

        assert "corrupted" in exc_info.value.reason.lower() or "unreadable" in exc_info.value.reason.lower()

    def test_password_protected_pdf(self, tmp_path):
        encrypted_file = tmp_path / "protected.pdf"

        # Create an encrypted PDF using PyMuPDF
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Confidential Bank Statement")
        # Save with password encryption
        doc.save(
            str(encrypted_file),
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw="password123",
            owner_pw="owner123",
        )
        doc.close()

        with pytest.raises(PasswordProtectedPDFError) as exc_info:
            validate_pdf_file(str(encrypted_file))

        assert "password" in exc_info.value.reason.lower() or "encrypted" in exc_info.value.reason.lower()

    def test_pdf_without_transactions_yields_empty_list(self, tmp_path):
        """A normal document (e.g. essay) should yield zero transactions."""
        text_doc_path = tmp_path / "essay.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "This is an essay about economics and financial history.")
        page.insert_text((50, 70), "No tabular bank transactions exist in this document.")
        doc.save(str(text_doc_path))
        doc.close()

        txns = extract_transactions(str(text_doc_path))
        assert len(txns) == 0
