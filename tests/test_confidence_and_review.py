"""Unit tests for confidence scoring and low-confidence review flagging."""

import pytest
from app.models import Transaction, ClassificationMethod, ValidationStatus
from app.classification.classifier import classify_transaction, REVIEW_THRESHOLD
from app.classification.ml_classifier import load_model
from app.normalization.transaction_normalizer import transactions_to_dataframe


@pytest.fixture(scope="module")
def ml_model():
    return load_model()


class TestConfidenceAndReview:
    """Verifies confidence output and 'Needs Review' tagging for low confidence (< 0.60)."""

    def test_rule_match_has_perfect_confidence_and_verified(self, ml_model):
        """Rule match -> 1.00 confidence, Verified (no review needed)."""
        txn = Transaction(description="SWIGGY PAYMENT FOOD ORDER")
        classified = classify_transaction(txn, ml_model=ml_model)

        assert classified.category == "Food & Dining"
        assert classified.classification_method == ClassificationMethod.RULE_BASED
        assert classified.confidence == 1.00
        assert classified.needs_review is False
        assert classified.review_status == "Verified"

    def test_low_confidence_triggers_needs_review(self, ml_model):
        """Ambiguous / novel description with confidence < 0.60 -> Needs Review."""
        txn = Transaction(description="UNKNOWN RANDOM COUNTERPARTY 998811")
        classified = classify_transaction(txn, ml_model=ml_model)

        assert classified.classification_method == ClassificationMethod.ML_MODEL
        # For a completely unknown random string, probability is distributed across 14 classes (< 0.60)
        assert classified.confidence < REVIEW_THRESHOLD
        assert classified.needs_review is True
        assert classified.review_status == "Needs Review"
        assert any("Needs Review" in n for n in classified.validation_notes)

    def test_invalid_transaction_stays_in_review_after_high_confidence_rule(self, ml_model):
        txn = Transaction(
            description="SWIGGY PAYMENT FOOD ORDER",
            validation_status=ValidationStatus.INVALID,
            needs_review=True,
        )

        classified = classify_transaction(txn, ml_model=ml_model)

        assert classified.confidence == 1.0
        assert classified.validation_status == ValidationStatus.INVALID
        assert classified.needs_review is True

    def test_dataframe_contains_confidence_and_review_status(self, ml_model):
        """Verifies that DataFrame outputs format category, method, confidence, and review_status."""
        txns = [
            Transaction(description="DOMINOS PIZZA"),
            Transaction(description="XYZ MYSTERIOUS CORP 101"),
        ]
        for t in txns:
            classify_transaction(t, ml_model=ml_model)

        df = transactions_to_dataframe(txns)

        assert "category" in df.columns
        assert "classification_method" in df.columns
        assert "confidence" in df.columns
        assert "review_status" in df.columns

        # Dominos pizza row
        assert df.iloc[0]["category"] == "Food & Dining"
        assert df.iloc[0]["classification_method"] == "rule_based"
        assert df.iloc[0]["confidence"] == 1.00
        assert df.iloc[0]["review_status"] == "Verified"

        # Unknown row
        assert df.iloc[1]["review_status"] == "Needs Review"
