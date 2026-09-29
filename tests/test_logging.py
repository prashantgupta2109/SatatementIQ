"""Unit tests for pipeline logging."""

import logging
import os
import pytest
from app.pipeline import process_pdf_pipeline
from app.logging_config import setup_logging, get_logger


class TestPipelineLogging:
    """Verifies that all pipeline stages emit clear INFO log messages."""

    def test_pipeline_emits_expected_log_messages(self, caplog):
        caplog.set_level(logging.INFO, logger="bank_processor")

        pdf_path = "data/sample_statement.pdf"
        result = process_pdf_pipeline(pdf_path, original_filename="statement.pdf")

        log_messages = [rec.message for rec in caplog.records if rec.name == "bank_processor"]

        # Check for each milestone message
        assert any("Processing statement.pdf" in m for m in log_messages)
        assert any("Detected PDF type: text" in m for m in log_messages)
        assert any("Extracted 10 transactions" in m for m in log_messages)
        assert any("Normalization completed" in m for m in log_messages)
        assert any("Validation completed" in m for m in log_messages)
        assert any("Rule classifier:" in m for m in log_messages)
        assert any("ML classifier:" in m for m in log_messages)

    def test_pipeline_with_export_logs_export_completed(self, caplog, tmp_path):
        """Verifies end-to-end milestone emission including 'Export completed'."""
        caplog.set_level(logging.INFO, logger="bank_processor")

        pdf_path = "data/sample_statement.pdf"
        export_file = str(tmp_path / "out.csv")
        result = process_pdf_pipeline(pdf_path, original_filename="statement.pdf", export_path=export_file)

        log_messages = [rec.message for rec in caplog.records if rec.name == "bank_processor"]

        assert any("Processing statement.pdf" in m for m in log_messages)
        assert any("Detected PDF type: text" in m for m in log_messages)
        assert any("Extracted 10 transactions" in m for m in log_messages)
        assert any("Normalization completed" in m for m in log_messages)
        assert any("Validation completed" in m for m in log_messages)
        assert any("Rule classifier:" in m for m in log_messages)
        assert any("ML classifier:" in m for m in log_messages)
        assert any("Export completed" in m for m in log_messages)

    def test_csv_export_direct_logging(self, caplog, tmp_path):
        """Verifies direct export_to_csv logs 'Export completed'."""
        from app.export.csv_exporter import export_to_csv
        from app.models import Transaction

        caplog.set_level(logging.INFO, logger="bank_processor")
        out_file = str(tmp_path / "test.csv")
        export_to_csv([Transaction(description="TEST")], output_path=out_file)

        log_messages = [rec.message for rec in caplog.records if rec.name == "bank_processor"]
        assert any("Export completed" in m for m in log_messages)

    def test_excel_export_direct_logging(self, caplog, tmp_path):
        """Verifies direct export_to_excel logs 'Export completed'."""
        from app.export.excel_exporter import export_to_excel
        from app.models import Transaction, BankAccount

        caplog.set_level(logging.INFO, logger="bank_processor")
        out_file = str(tmp_path / "test.xlsx")
        export_to_excel([Transaction(description="TEST")], BankAccount(), output_path=out_file)

        log_messages = [rec.message for rec in caplog.records if rec.name == "bank_processor"]
        assert any("Export completed" in m for m in log_messages)

    def test_logging_formatter_format(self):
        """Verifies log format strings produce 'INFO  <message>' with standard spacing."""
        from app.logging_config import _LOG_FORMAT
        formatter = logging.Formatter(_LOG_FORMAT)
        record = logging.LogRecord(
            name="bank_processor",
            level=logging.INFO,
            pathname="pipeline.py",
            lineno=50,
            msg="Processing statement.pdf",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert formatted == "INFO  Processing statement.pdf"

    def test_setup_logging_with_file(self, tmp_path):
        """Verifies that setup_logging successfully attaches a FileHandler and writes logs."""
        log_file = str(tmp_path / "test_run.log")
        logger = setup_logging(level=logging.INFO, log_file=log_file)
        logger.info("Test log entry to file")

        # Flush handlers
        for handler in logger.handlers:
            handler.flush()

        assert os.path.exists(log_file)
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Test log entry to file" in content
