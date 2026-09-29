"""Custom domain exceptions for Bank Statement Processing.

Provides structured, user-facing error messages instead of raw tracebacks.
"""

from typing import Optional


class BankStatementError(Exception):
    """Base exception for all bank statement processing failures."""

    def __init__(
        self,
        reason: str,
        suggestion: str = "Please upload a supported bank statement.",
    ):
        self.reason = reason
        self.suggestion = suggestion
        super().__init__(f"Unable to process this statement. Reason: {reason}")


class InvalidPDFError(BankStatementError):
    """Raised when the uploaded file is not a valid PDF document."""
    def __init__(self, reason: str = "The uploaded file is not a valid PDF document."):
        super().__init__(
            reason=reason,
            suggestion="Please ensure you upload a valid .pdf file downloaded from your bank.",
        )


class PasswordProtectedPDFError(BankStatementError):
    """Raised when the PDF statement is encrypted or password-protected."""
    def __init__(self, reason: str = "The PDF is password-protected or encrypted."):
        super().__init__(
            reason=reason,
            suggestion="Please remove the password from your statement or export an unencrypted copy before uploading.",
        )


class EmptyPDFError(BankStatementError):
    """Raised when the PDF has 0 bytes or contains 0 pages."""
    def __init__(self, reason: str = "The PDF contains no pages or zero data."):
        super().__init__(
            reason=reason,
            suggestion="Please check that the file is not empty and contains your transaction activity.",
        )


class CorruptedPDFError(BankStatementError):
    """Raised when PDF syntax is broken and cannot be parsed."""
    def __init__(self, reason: str = "The PDF file is corrupted or unreadable."):
        super().__init__(
            reason=reason,
            suggestion="Please re-download a fresh copy of your bank statement from your netbanking portal.",
        )


class OCRError(BankStatementError):
    """Raised when OCR fails or Tesseract engine is unavailable."""
    def __init__(self, reason: str = "Scanned PDF could not be processed by OCR engine."):
        super().__init__(
            reason=reason,
            suggestion="Please ensure Tesseract-OCR is installed or provide a text-based PDF statement.",
        )


class NoTransactionsFoundError(BankStatementError):
    """Raised when no valid transactions could be extracted from the document."""
    def __init__(self, reason: str = "No transaction table could be detected."):
        super().__init__(
            reason=reason,
            suggestion="Please upload a supported bank statement containing a visible transaction table.",
        )


class UnsupportedFormatError(BankStatementError):
    """Raised when the document layout lacks identifiable financial columns."""
    def __init__(self, reason: str = "Unsupported statement layout or missing required financial columns."):
        super().__init__(
            reason=reason,
            suggestion="Please upload an account statement from a supported bank (e.g. HDFC, SBI, ICICI, Axis).",
        )
