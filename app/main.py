"""Streamlit Web Application for Bank Statement Processing & Classification.

Provides an interactive user interface to:
1. Upload and detect bank statements (text-based or scanned PDFs)
2. Extract account identity metadata
3. Extract and normalize financial transactions
4. Validate data consistency and running balances
5. Classify transactions using Hybrid Rules + ML (Non-LLM)
6. Preview structured records with review flags
7. Export processed results to Excel (.xlsx) and CSV (.csv)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import tempfile
import pandas as pd
import streamlit as st

st.markdown(
    """
    <style>
    div[data-testid="stMetric"] > div {
        padding: 0.5rem 0.6rem;
    }
    div[data-testid="stMetric"] label {
        font-size: 0.9rem !important;
        font-weight: 500;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 2.0rem !important;
        line-height: 1.2;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

from app.models import ProcessingResult, BankAccount, Transaction
from app.ingestion.image_converter import image_bytes_to_pdf
from app.ingestion.pdf_detector import detect_pdf_type, get_page_count
from app.extraction.text_extractor import extract_pages_text, extract_account_info
from app.extraction.table_extractor import extract_transactions as extract_text_transactions
from app.extraction.ocr_extractor import extract_from_scanned_pdf, is_tesseract_available
from app.normalization.transaction_normalizer import normalize_transactions, transactions_to_dataframe
from app.validation.transaction_validator import validate_all_transactions
from app.classification.classifier import classify_transactions
from app.export.csv_exporter import export_to_csv_bytes, transactions_to_export_dataframe
from app.export.excel_exporter import export_to_excel_bytes


st.set_page_config(
    page_title="STATEMENTIQ | Bank Statement Intelligence",
    page_icon="🏦",
    layout="wide",
)


from app.exceptions import (
    BankStatementError,
    NoTransactionsFoundError,
    OCRError,
)
from app.pipeline import process_pdf_pipeline
from app.logging_config import get_logger

logger = get_logger("bank_processor")


def process_statement(uploaded_file) -> ProcessingResult:
    """Process an uploaded PDF or convert an image upload for OCR processing."""
    uploaded_bytes = uploaded_file.getvalue()
    extension = os.path.splitext(uploaded_file.name)[1].lower()
    if extension != ".pdf":
        if not is_tesseract_available():
            raise OCRError(
                "Image uploads require Tesseract OCR, but it is not installed or available."
            )
        uploaded_bytes = image_bytes_to_pdf(uploaded_bytes)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_bytes)
        tmp_path = tmp.name

    try:
        return process_pdf_pipeline(tmp_path, original_filename=uploaded_file.name)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def main():
    st.title("STATEMENTIQ")
    st.caption("Bank Statement Intelligence")

    with st.sidebar:
        st.header("⚙️ System Status")
        st.success("Classification Engine: Rules + ML")
        st.info("LLM Integration: Disabled (Per Specification)")
        ocr_ready = is_tesseract_available()
        if ocr_ready:
            st.success("OCR Engine: Tesseract Available")
        else:
            st.warning("OCR Engine: Tesseract Optional (Install for scanned PDFs)")

        st.markdown("---")
        st.markdown("**Exports:** Excel (`.xlsx`) and CSV (`.csv`)")

    st.subheader("1. Upload PDF or Image")
    uploaded_file = st.file_uploader(
        "Choose a bank statement PDF or image",
        type=["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
        help="Images are converted temporarily and processed with Tesseract OCR.",
    )

    if uploaded_file is not None:
        if st.session_state.get("filename") != uploaded_file.name:
            st.session_state.pop("result", None)
            st.session_state.pop("filename", None)

        process_btn = st.button("Process Statement", type="primary")

        if process_btn:
            st.session_state.pop("result", None)
            with st.spinner("Processing document through extraction & classification pipeline..."):
                try:
                    res = process_statement(uploaded_file)
                    st.session_state["result"] = res
                    st.session_state["filename"] = uploaded_file.name
                except BankStatementError as err:
                    st.session_state.pop("result", None)
                    st.error(
                        f"### ⚠️ Unable to process this statement.\n\n"
                        f"**Reason:**\n{err.reason}\n\n"
                        f"{err.suggestion}"
                    )
                except Exception as exc:
                    st.session_state.pop("result", None)
                    st.error(
                        "### ⚠️ Unable to process this statement.\n\n"
                        "**Reason:**\nNo transaction table could be detected.\n\n"
                        "Please upload a supported bank statement."
                    )

    if "result" in st.session_state:
        res: ProcessingResult = st.session_state["result"]
        txns = res.transactions

        st.markdown("---")
        st.subheader("2. Processing Pipeline")
        st.success("Statement processed")
        stage_cols = st.columns(4)
        for column, stage in zip(stage_cols, ("Extract", "Normalize", "Validate", "Classify")):
            column.markdown(f"**✓ {stage}**")

        review_needed_count = sum(1 for t in txns if t.needs_review)
        classified_count = sum(1 for t in txns if t.category and t.category != "Uncategorized")

        st.markdown("---")
        st.subheader("3. Results")
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(
            """
            <div style='padding: 0.2rem 0.4rem;'><div style='font-size: 1.1rem; font-weight: 600; color: #4a4a4a;'>PDF Type</div>
            <div style='font-size: 2.2rem; font-weight: 700; margin-top: 0.2rem;'>Text-Based</div></div>
            """
            if res.pdf_type == "text"
            else """
            <div style='padding: 0.2rem 0.4rem;'><div style='font-size: 1.1rem; font-weight: 600; color: #4a4a4a;'>PDF Type</div>
            <div style='font-size: 1.8rem; font-weight: 700; margin-top: 0.2rem;'>Scanned (Image)</div></div>
            """,
            unsafe_allow_html=True,
        )
        m2.metric("Transactions", len(txns))
        m3.metric("Classified", classified_count)
        m4.metric("Needs Review", review_needed_count)

        if res.errors:
            for err in res.errors:
                st.warning(err)

        st.markdown("---")
        st.subheader("Account Information")
        acc = res.account
        a1, a2, a3, a4, a5 = st.columns(5)
        a1.text_input("Bank", value=acc.bank_name or "Unknown", disabled=True)
        a2.text_input("Account Holder", value=acc.account_holder or "Unknown", disabled=True)
        a3.text_input("Account Number", value=acc.account_number or "Unknown", disabled=True)
        a4.text_input("IFSC", value=acc.ifsc or "Unknown", disabled=True)
        a5.text_input("Statement Period", value=acc.statement_period or "Unknown", disabled=True)

        st.subheader("Transactions and Classification")
        if txns:
            df_display = transactions_to_export_dataframe(txns)
            df_display["Review Status"] = [txn.review_status for txn in txns]
            df_display["Validation Notes"] = ["; ".join(txn.validation_notes) for txn in txns]

            transactions_tab, classification_tab, review_tab, analytics_tab = st.tabs(
                ["Transactions", "Classification", "Review", "Analytics"]
            )

            with transactions_tab:
                f1, f2 = st.columns(2)
                categories = ["All"] + sorted(df_display["Category"].unique().tolist())
                methods = ["All"] + sorted(df_display["Classification Method"].unique().tolist())
                selected_cat = f1.selectbox("Category", categories)
                selected_method = f2.selectbox("Method", methods)

                filtered_df = df_display.copy()
                if selected_cat != "All":
                    filtered_df = filtered_df[filtered_df["Category"] == selected_cat]
                if selected_method != "All":
                    filtered_df = filtered_df[filtered_df["Classification Method"] == selected_method]
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)

            with classification_tab:
                rule_count = sum(1 for txn in txns if txn.classification_method.value == "rule_based")
                ml_count = sum(1 for txn in txns if txn.classification_method.value == "ml_model")
                c1, c2, c3 = st.columns(3)
                c1.metric("Rule Classified", rule_count)
                c2.metric("ML Classified", ml_count)
                c3.metric("Average Confidence", f"{df_display['Confidence'].astype(float).mean():.2f}")
                st.dataframe(
                    pd.crosstab(df_display["Category"], df_display["Classification Method"]),
                    use_container_width=True,
                )

            with review_tab:
                review_mask = [
                    txn.needs_review or txn.validation_status.value != "valid"
                    for txn in txns
                ]
                review_df = df_display.loc[review_mask]
                if review_df.empty:
                    st.success("No transactions require review.")
                else:
                    st.dataframe(review_df, use_container_width=True, hide_index=True)

            with analytics_tab:
                st.bar_chart(df_display["Category"].value_counts())

            st.markdown("---")
            st.subheader("Download Results")
            d_col1, d_col2 = st.columns(2)

            csv_data = export_to_csv_bytes(txns)
            excel_data = export_to_excel_bytes(txns, acc)
            base_name = os.path.splitext(st.session_state.get("filename", "statement"))[0]

            with d_col1:
                st.download_button(
                    label="Download Excel (.xlsx)",
                    data=excel_data,
                    file_name=f"{base_name}_analysis.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            with d_col2:
                st.download_button(
                    label="Download CSV (.csv)",
                    data=csv_data,
                    file_name=f"{base_name}_classified.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        else:
            st.info("No transaction rows extracted from the uploaded document.")


if __name__ == "__main__":
    main()
