"""End-to-End Bank Statement Processing Pipeline Orchestrator.

Coordinates ingestion, extraction, normalization, validation,
classification, and export with comprehensive Python standard logging.
"""

import os
from typing import Optional

from app.models import ProcessingResult, Transaction, ClassificationMethod
from app.exceptions import (
    BankStatementError,
    NoTransactionsFoundError,
)
from app.ingestion.pdf_validator import validate_pdf_file
from app.ingestion.pdf_detector import detect_pdf_type
from app.extraction.text_extractor import extract_pages_text, extract_account_info
from app.extraction.table_extractor import extract_transactions as extract_text_transactions
from app.extraction.ocr_extractor import extract_from_scanned_pdf, is_tesseract_available
from app.normalization.transaction_normalizer import normalize_transactions
from app.validation.transaction_validator import validate_all_transactions
from app.classification.classifier import classify_transactions
from app.logging_config import get_logger

logger = get_logger("bank_processor")


def process_pdf_pipeline(
    pdf_path: str,
    original_filename: Optional[str] = None,
    export_path: Optional[str] = None,
) -> ProcessingResult:
    """Execute the end-to-end processing pipeline on a bank statement file.

    Logs progress at each milestone using Python's standard logging module:
        INFO  Processing <filename>
        INFO  Detected PDF type: <text|image>
        INFO  Extracted <N> transactions
        INFO  Normalization completed
        INFO  Validation completed
        INFO  Rule classifier: <N> transactions
        INFO  ML classifier: <N> transactions
        INFO  Export completed

    Args:
        pdf_path: Path to the target PDF file on disk.
        original_filename: User-friendly filename for logging.
        export_path: Optional file path to export transactions (.csv or .xlsx).

    Returns:
        ProcessingResult dataclass with extracted account and transactions.
    """
    display_name = original_filename or os.path.basename(pdf_path)
    logger.info("Processing %s", display_name)

    result = ProcessingResult()

    # Pre-flight document validation (catches encrypted, corrupted, empty, invalid files)
    doc = validate_pdf_file(pdf_path)
    result.page_count = len(doc)
    doc.close()

    # 1. Detection
    result.pdf_type = detect_pdf_type(pdf_path)
    logger.info("Detected PDF type: %s", result.pdf_type)

    raw_txns: list[Transaction] = []

    # 2. Extraction according to detected type
    if result.pdf_type == "text":
        pages_text = extract_pages_text(pdf_path)
        result.account = extract_account_info(pages_text)
        raw_txns = extract_text_transactions(pdf_path)
    else:
        # Scanned / Image-based
        if not is_tesseract_available():
            result.errors.append(
                "Detected scanned PDF, but Tesseract OCR is not installed. "
                "Processing with fallback text extraction."
            )
            pages_text = extract_pages_text(pdf_path)
            result.account = extract_account_info(pages_text)
            raw_txns = extract_text_transactions(pdf_path)
        else:
            account, txns = extract_from_scanned_pdf(pdf_path)
            result.account = account
            raw_txns = txns

    logger.info("Extracted %d transactions", len(raw_txns))

    if not raw_txns:
        raise NoTransactionsFoundError("No transaction table could be detected.")

    # 3. Normalization
    normalized = normalize_transactions(raw_txns)
    if not normalized:
        raise NoTransactionsFoundError("Extracted rows did not contain valid date-stamped transactions.")
    logger.info("Normalization completed")

    # 4. Validation
    validated = validate_all_transactions(normalized)
    logger.info("Validation completed")

    # 5. Hybrid Classification (Rules + ML)
    classified = classify_transactions(validated)

    rule_count = sum(1 for t in classified if t.classification_method == ClassificationMethod.RULE_BASED)
    ml_count = sum(1 for t in classified if t.classification_method == ClassificationMethod.ML_MODEL)

    logger.info("Rule classifier: %d transactions", rule_count)
    logger.info("ML classifier: %d transactions", ml_count)

    result.transactions = classified
    if export_path:
        if export_path.lower().endswith(".xlsx"):
            from app.export.excel_exporter import export_to_excel
            export_to_excel(classified, result.account, output_path=export_path)
        else:
            from app.export.csv_exporter import export_to_csv
            export_to_csv(classified, output_path=export_path)

    return result


if __name__ == "__main__":
    import sys
    from app.logging_config import setup_logging

    setup_logging()
    target_pdf = sys.argv[1] if len(sys.argv) > 1 else "data/sample_statement.pdf"
    target_export = sys.argv[2] if len(sys.argv) > 2 else "transactions.csv"
    if os.path.exists(target_pdf):
        process_pdf_pipeline(target_pdf, export_path=target_export)
    else:
        print(f"File not found: {target_pdf}")
