"""Unit tests for ML transaction classifier (TF-IDF + Logistic Regression)."""

import pytest
from app.models import Transaction, ClassificationMethod
from app.classification.ml_classifier import (
    clean_text_for_ml,
    predict_text,
    classify_with_ml,
    load_model,
)


@pytest.fixture(scope="module")
def ml_model():
    return load_model()


class TestMLPreprocessing:
    """Verifies text normalization before vectorization."""

    def test_clean_text_for_ml(self):
        raw = "UPI-SWIGGY-12948/Bangalore! ORDER"
        cleaned = clean_text_for_ml(raw)
        assert "swiggy" in cleaned
        assert "bangalore" in cleaned
        assert "order" in cleaned
        assert "!" not in cleaned
        assert "/" not in cleaned


class TestMLPredictions:
    """Verifies predictions on representative transaction descriptions."""

    def test_swiggy_prediction(self, ml_model):
        category, confidence = predict_text("SWIGGY ORDER", model=ml_model)
        assert category == "Food & Dining"
        assert confidence > 0.15

    def test_amazon_prediction(self, ml_model):
        category, confidence = predict_text("AMAZON PURCHASE", model=ml_model)
        assert category == "Shopping"
        assert confidence > 0.15

    def test_netflix_prediction(self, ml_model):
        category, confidence = predict_text("NETFLIX SUBSCRIPTION", model=ml_model)
        assert category == "Entertainment"
        assert confidence > 0.15

    def test_uber_prediction(self, ml_model):
        category, confidence = predict_text("UBER RIDE", model=ml_model)
        assert category == "Travel"
        assert confidence > 0.15

    def test_electricity_prediction(self, ml_model):
        category, confidence = predict_text("ELECTRICITY BILL", model=ml_model)
        assert category == "Utilities"
        assert confidence > 0.15


class TestMLBatchClassification:
    """Verifies that Transaction objects receive ML metadata."""

    def test_classify_with_ml_updates_transaction(self, ml_model):
        txns = [
            Transaction(description="UBER TRIP TO AIRPORT"),
            Transaction(description="FLIPKART INTERNET ORDER"),
        ]

        results = classify_with_ml(txns, model=ml_model)

        assert results[0].category == "Travel"
        assert results[0].classification_method == ClassificationMethod.ML_MODEL
        assert results[0].confidence > 0.15

        assert results[1].category == "Shopping"
        assert results[1].classification_method == ClassificationMethod.ML_MODEL
        assert results[1].confidence > 0.15
