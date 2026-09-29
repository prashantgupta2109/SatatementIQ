"""Logging configuration for Bank Statement Processor.

Provides structured logging across all ingestion, extraction,
normalization, validation, classification, and export stages.
"""

import logging
import os
import sys
from typing import Optional

_LOG_FORMAT = "%(levelname)-5s %(message)s"
_DETAILED_FORMAT = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"

_initialized = False


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Configure root and application loggers.

    Args:
        level: Logging level (default INFO).
        log_file: Optional path to save persistent log entries.

    Returns:
        The configured logger instance.
    """
    global _initialized
    root_logger = logging.getLogger("bank_processor")
    root_logger.setLevel(level)

    # Ensure a clean console handler is registered
    has_console = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in root_logger.handlers
    )
    if not has_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root_logger.addHandler(console_handler)

    if log_file:
        abs_log_path = os.path.abspath(log_file)
        os.makedirs(os.path.dirname(abs_log_path), exist_ok=True)
        has_file = any(
            isinstance(h, logging.FileHandler) and os.path.abspath(getattr(h, "baseFilename", "")) == abs_log_path
            for h in root_logger.handlers
        )
        if not has_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(_DETAILED_FORMAT))
            root_logger.addHandler(file_handler)

    _initialized = True
    return root_logger


def get_logger(name: str = "bank_processor") -> logging.Logger:
    """Retrieve an application logger with consistent formatting."""
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)
