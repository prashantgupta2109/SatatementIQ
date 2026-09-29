"""Unit tests for transaction classification module (app.classification.classifier)."""

import pytest
from app.models import Transaction, ClassificationMethod
from app.classification.classifier import (
    classify_transaction,
    classify_transactions,
    REVIEW_THRESHOLD,
)
from app.classification.ml_classifier import load_model


@pytest.fixture(scope="module")
def ml_model():
    return load_model()


class TestClassifier:
    """Tests for hybrid transaction classifier (Rules + Machine Learning)."""

    def test_swiggy_to_food_and_dining(self, ml_model):
        """SWIGGY → Food & Dining"""
        txn = Transaction(description="SWIGGY")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Food & Dining"
        assert result.classification_method == ClassificationMethod.RULE_BASED
        assert result.confidence >= 0.8
        assert not result.needs_review

    def test_swiggy_order_variation(self, ml_model):
        """SWIGGY FOOD ORDER → Food & Dining"""
        txn = Transaction(description="SWIGGY FOOD ORDER BANGALORE")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Food & Dining"
        assert result.classification_method == ClassificationMethod.RULE_BASED

    def test_amazon_to_shopping(self, ml_model):
        """AMAZON → Shopping"""
        txn = Transaction(description="AMAZON")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Shopping"
        assert result.classification_method == ClassificationMethod.RULE_BASED
        assert result.confidence >= 0.8
        assert not result.needs_review

    def test_amazon_marketplace_variation(self, ml_model):
        """AMAZON PAY / RETAIL → Shopping"""
        txn = Transaction(description="AMAZON PAY INDIA PVT LTD")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Shopping"
        assert result.classification_method == ClassificationMethod.RULE_BASED

    def test_netflix_to_entertainment(self, ml_model):
        txn = Transaction(description="NETFLIX SUBSCRIPTION")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Entertainment"
        assert result.classification_method == ClassificationMethod.RULE_BASED

    def test_uber_to_travel(self, ml_model):
        txn = Transaction(description="UBER RIDE MUMBAI")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Travel"
        assert result.classification_method == ClassificationMethod.RULE_BASED

    def test_electricity_bill_to_utilities(self, ml_model):
        txn = Transaction(description="BESCOM ELECTRICITY BILL")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Utilities"
        assert result.classification_method == ClassificationMethod.RULE_BASED

    def test_salary_credit_to_salary(self, ml_model):
        txn = Transaction(description="SALARY CREDIT CORP ACME")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Salary"
        assert result.classification_method == ClassificationMethod.RULE_BASED

    def test_mutual_fund_to_investment(self, ml_model):
        txn = Transaction(description="SIP PURCHASE ZERODHA MUTUAL FUND")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category == "Investment"
        assert result.classification_method == ClassificationMethod.RULE_BASED

    def test_ml_fallback_for_novel_merchant(self, ml_model):
        """Unrecognized merchant falls back to ML classifier."""
        txn = Transaction(description="XPERTS CONSULTING FEE")
        result = classify_transaction(txn, ml_model=ml_model)

        # Category can be any valid ML prediction
        assert result.category is not None
        assert result.classification_method == ClassificationMethod.ML_MODEL
        assert result.confidence > 0.0

    def test_batch_classification(self, ml_model):
        txns = [
            Transaction(description="SWIGGY"),
            Transaction(description="AMAZON"),
            Transaction(description="AIRTEL BROADBAND BILL"),
        ]

        results = classify_transactions(txns, ml_model=ml_model)

        assert len(results) == 3
        assert results[0].category == "Food & Dining"
        assert results[1].category == "Shopping"
        assert results[2].category == "Utilities"

    def test_empty_description_handling(self, ml_model):
        txn = Transaction(description="")
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category is not None
        assert result.confidence >= 0.0

    def test_none_description_handling(self, ml_model):
        txn = Transaction(description=None)
        result = classify_transaction(txn, ml_model=ml_model)

        assert result.category is not None
        assert result.confidence >= 0.0
