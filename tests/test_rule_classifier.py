"""Unit tests for rule-based transaction classifier."""

import pytest
from app.models import Transaction, ClassificationMethod
from app.classification.rule_classifier import classify_text, classify_transaction, classify_transactions


class TestRuleClassifierKeywords:
    """Verifies keyword mappings across the 14 standard categories."""

    def test_food_and_dining(self):
        for desc in ["UPI-SWIGGY-1234", "POS ZOMATO RESTAURANT", "DOMINOS PIZZA OUTLET"]:
            cat, conf = classify_text(desc)
            assert cat == "Food & Dining"
            assert conf >= 0.9

    def test_shopping(self):
        for desc in ["AMAZON PAY RETAIL", "FLIPKART INTERNET BLR", "MYNTRA DESIGNS"]:
            cat, conf = classify_text(desc)
            assert cat == "Shopping"
            assert conf >= 0.9

    def test_entertainment(self):
        for desc in ["NETFLIX MONTHLY SUB", "SPOTIFY AB SWEDEN", "BOOKMYSHOW TICKETS"]:
            cat, conf = classify_text(desc)
            assert cat == "Entertainment"
            assert conf >= 0.9

    def test_travel(self):
        for desc in ["UBER TRIP MUMBAI", "OLA RIDES BANGALORE", "NETC FASTAG RECHARGE"]:
            cat, conf = classify_text(desc)
            assert cat == "Travel"
            assert conf >= 0.9

    def test_utilities(self):
        for desc in ["BESCOM ELECTRICITY BILL", "AIRTEL PREPAID RECHARGE", "IGL GAS BILL"]:
            cat, conf = classify_text(desc)
            assert cat == "Utilities"
            assert conf >= 0.9

    def test_salary(self):
        for desc in ["SALARY CREDIT MARCH 2026", "CORP SALARY INFOSYS"]:
            cat, conf = classify_text(desc)
            assert cat == "Salary"
            assert conf >= 0.9

    def test_investment(self):
        for desc in ["ZERODHA BROKING LTD", "GROWW MUTUAL FUND SIP"]:
            cat, conf = classify_text(desc)
            assert cat == "Investment"
            assert conf >= 0.9

    def test_merchant_over_transfer_priority(self):
        """When UPI rail co-occurs with merchant, merchant category wins."""
        desc = "UPI/234982/SWIGGY/BANGALORE"
        cat, _ = classify_text(desc)
        assert cat == "Food & Dining"

        desc2 = "UPI/984211/AMAZON/ORDER"
        cat2, _ = classify_text(desc2)
        assert cat2 == "Shopping"

    def test_pure_transfer(self):
        desc = "UPI/P2P/NEHA/PAYMENT"
        cat, _ = classify_text(desc)
        assert cat == "Transfer"

    def test_unmatched_falls_through_for_ml(self):
        desc = "MISCELLANEOUS CONTINGENCY EXPENSE 9821"
        cat, conf = classify_text(desc)
        assert cat is None
        assert conf == 0.0


class TestTransactionModelClassification:
    """Verifies that Transaction objects are updated with classification metadata."""

    def test_classify_transaction_updates_metadata(self):
        txn = Transaction(description="DOMINOS INDIA ONLINE")
        classified = classify_transaction(txn)

        assert classified.category == "Food & Dining"
        assert classified.classification_method == ClassificationMethod.RULE_BASED
        assert classified.confidence >= 0.9

    def test_classify_transactions_batch(self):
        txns = [
            Transaction(description="SWIGGY INSTAMART"),
            Transaction(description="NETFLIX.COM"),
            Transaction(description="UNKNOWN MERCHANT X77"),
        ]

        results = classify_transactions(txns)

        assert results[0].category == "Food & Dining"
        assert results[0].classification_method == ClassificationMethod.RULE_BASED

        assert results[1].category == "Entertainment"
        assert results[1].classification_method == ClassificationMethod.RULE_BASED

        # Unknown remains unclassified for ML step
        assert results[2].category == "Uncategorized"
        assert results[2].classification_method == ClassificationMethod.UNCLASSIFIED
