"""Unit tests for hybrid (Rules + ML) transaction classifier."""

import pytest
from app.models import Transaction, ClassificationMethod
from app.classification.classifier import classify_transaction, classify_transactions
from app.classification.ml_classifier import load_model


@pytest.fixture(scope="module")
def ml_model():
    return load_model()


class TestHybridClassifier:
    """Verifies two-layer routing between Rule heuristics and Machine Learning."""

    def test_strong_rule_match_uses_rule_engine(self, ml_model):
        """SWIGGY PAYMENT -> Rule -> Food & Dining (method=rule_based)."""
        txn = Transaction(description="SWIGGY PAYMENT")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Food & Dining"
        assert result.classification_method == ClassificationMethod.RULE_BASED
        assert result.confidence >= 0.9

    def test_unmatched_rule_falls_back_to_ml_model(self, ml_model):
        """UPI/XYZ/MARKETPLACE -> No rule -> ML -> Shopping (method=ml_model)."""
        txn = Transaction(description="UPI/XYZ/MARKETPLACE")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Shopping"
        assert result.classification_method == ClassificationMethod.ML_MODEL
        assert result.confidence > 0.15

    def test_batch_classification_hybrid(self, ml_model):
        """Processes a mix of deterministic rule matches and novel ML patterns."""
        txns = [
            Transaction(description="NETFLIX STREAMING BILL"),  # Rule -> Entertainment
            Transaction(description="BESCOM ONLINE PAYMENT"),    # Rule -> Utilities
            Transaction(description="NEW APPAREL MARKETPLACE"),  # ML -> Shopping
        ]

        results = classify_transactions(txns, ml_model=ml_model)

        # 1. Netflix
        assert results[0].category == "Entertainment"
        assert results[0].classification_method == ClassificationMethod.RULE_BASED

        # 2. Bescom
        assert results[1].category == "Utilities"
        assert results[1].classification_method == ClassificationMethod.RULE_BASED

        # 3. Marketplace
        assert results[2].category == "Shopping"
        assert results[2].classification_method == ClassificationMethod.ML_MODEL
