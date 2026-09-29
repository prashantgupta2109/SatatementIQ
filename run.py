"""Entry point for the Bank Statement Processor application."""

import os
import subprocess
import sys


def main():
    """Launch the Streamlit application or execute processing pipeline directly."""
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(".pdf"):
        from app.logging_config import setup_logging
        from app.pipeline import process_pdf_pipeline

        setup_logging()
        pdf_path = sys.argv[1]
        export_path = sys.argv[2] if len(sys.argv) > 2 else "transactions.csv"
        process_pdf_pipeline(pdf_path, export_path=export_path)
        return

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "app/main.py"],
        check=True,
    )


if __name__ == "__main__":
    main()
