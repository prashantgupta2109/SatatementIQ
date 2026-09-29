"""Hybrid Two-Layer Transaction Classifier.

Combines deterministic rule-based heuristics with traditional Machine Learning
(TF-IDF + Logistic Regression) without relying on Large Language Models (LLMs).

Pipeline:
    Transaction
         ↓
    Rule Classifier
         ↓
    Strong rule match?
     ┌───┴────┐
    YES       NO
     │         │
     ↓         ↓
    Category   ML Classifier
     (Rule)    ↓
               Category + Confidence (ML)
"""

from typing import List, Optional
from sklearn.pipeline import Pipeline

from app.models import Transaction, ClassificationMethod, ValidationStatus
from app.classification.rule_classifier import classify_text as rule_classify_text
from app.classification.ml_classifier import predict_text, load_model


REVIEW_THRESHOLD: float = 0.60


def classify_transaction(
    txn: Transaction,
    ml_model: Optional[Pipeline] = None,
    rule_min_confidence: float = 0.8,
) -> Transaction:
    """Classify a single transaction using the two-layer hybrid strategy.

    Layer 1: Rule-Based Classifier
        If a keyword/regex rule matches with strong confidence (>= 0.8),
        assign the category immediately with ClassificationMethod.RULE_BASED (1.00 confidence).

    Layer 2: Traditional ML Model (TF-IDF + Logistic Regression)
        If no rule matches, fallback to the pre-trained ML model and
        assign the category with ClassificationMethod.ML_MODEL and calculated confidence.

    Low Confidence Flagging:
        If confidence < 0.60, transaction is marked with needs_review = True
        and tagged as 'Needs Review'.
    """
    desc = txn.description or ""

    # Layer 1: Rule-based check
    rule_category, rule_conf = rule_classify_text(desc)

    if rule_category is not None and rule_conf >= rule_min_confidence:
        txn.category = rule_category
        txn.classification_method = ClassificationMethod.RULE_BASED
        txn.confidence = float(rule_conf)
    else:
        # Layer 2: Machine Learning fallback
        ml_category, ml_conf = predict_text(desc, model=ml_model)
        txn.category = ml_category
        txn.classification_method = ClassificationMethod.ML_MODEL
        txn.confidence = round(float(ml_conf), 4)

    # Flag low-confidence predictions
    if txn.confidence < REVIEW_THRESHOLD:
        txn.needs_review = True
        review_note = f"Low confidence ({txn.confidence:.2f} < {REVIEW_THRESHOLD:.2f}): Needs Review"
        if review_note not in txn.validation_notes:
            txn.validation_notes.append(review_note)
    else:
        txn.needs_review = txn.validation_status != ValidationStatus.VALID

    return txn


def classify_transactions(
    transactions: List[Transaction],
    ml_model: Optional[Pipeline] = None,
) -> List[Transaction]:
    """Classify a batch of transactions using the hybrid rules + ML engine.

    Args:
        transactions: List of Transaction objects.
        ml_model: Optional pre-loaded ML pipeline.

    Returns:
        List of classified Transaction objects.
    """
    if not transactions:
        return transactions

    # Load ML model once for the batch
    if ml_model is None:
        ml_model = load_model()

    for txn in transactions:
        classify_transaction(txn, ml_model=ml_model)

    return transactions
