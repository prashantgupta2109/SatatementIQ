"""Rule-based transaction classification engine.

Matches transaction descriptions against configurable keyword rules
stored in app.classification.rules.

Priority logic ensures merchant/purpose categories (e.g., Food, Shopping)
take precedence over payment rail markers (e.g., UPI, NEFT).
"""

import re
from typing import List, Optional, Tuple

from app.models import Transaction, ClassificationMethod
from app.classification.rules import CATEGORY_RULES, CATEGORIES


# Priority ordering: specific merchant/purpose categories evaluated before generic transfer rails
_CATEGORY_EVALUATION_ORDER = [
    "Salary",
    "Food & Dining",
    "Shopping",
    "Entertainment",
    "Healthcare",
    "Travel",
    "Utilities",
    "Rent",
    "Education",
    "Investment",
    "Fees & Charges",
    "ATM/Cash",
    "Transfer",  # Checked last among rules so "UPI-SWIGGY" becomes Food, not Transfer
]


def _build_regex_for_keywords(keywords: List[str]) -> re.Pattern:
    """Compile regex pattern matching any keyword with word boundaries or punctuation boundaries."""
    # Sort keywords by length descending to match longest phrases first
    sorted_kws = sorted(keywords, key=len, reverse=True)
    escaped_kws = [re.escape(k) for k in sorted_kws]
    # Match keyword with boundaries (\b or delimiters like /, -, _, .)
    pattern_str = r"(?:\b|[\/\-_\.\s])(" + "|".join(escaped_kws) + r")(?:\b|[\/\-_\.\s]|$)"
    return re.compile(pattern_str, re.IGNORECASE)


# Precompile regex per category for high performance
_COMPILED_RULES = {
    category: _build_regex_for_keywords(CATEGORY_RULES[category])
    for category in _CATEGORY_EVALUATION_ORDER
    if category in CATEGORY_RULES
}


def classify_text(description: str) -> Tuple[Optional[str], float]:
    """Classify a raw transaction description string using keyword rules.

    Args:
        description: Transaction narration or description.

    Returns:
        Tuple of (category, confidence). Category is None if no rule matches.
    """
    if not description:
        return None, 0.0

    desc_upper = description.upper()

    for category in _CATEGORY_EVALUATION_ORDER:
        compiled_regex = _COMPILED_RULES.get(category)
        if compiled_regex and compiled_regex.search(desc_upper):
            # Generic transfer rails have moderate confidence to allow ML fallback for novel merchants
            conf = 0.75 if category == "Transfer" else 1.00
            return category, conf

    return None, 0.0


def classify_transaction(txn: Transaction) -> Transaction:
    """Classify a single Transaction object using rule-based heuristics.

    If matched:
        txn.category is set to matched category
        txn.classification_method is set to RULE_BASED
        txn.confidence is set to rule confidence (0.95)
    """
    cat, conf = classify_text(txn.description)
    if cat:
        txn.category = cat
        txn.classification_method = ClassificationMethod.RULE_BASED
        txn.confidence = conf

    return txn


def classify_transactions(transactions: List[Transaction]) -> List[Transaction]:
    """Classify a list of transactions using rule-based heuristics.

    Transactions that do not match any rule remain with their current classification
    so the ML model in the next layer can evaluate them.
    """
    for txn in transactions:
        classify_transaction(txn)
    return transactions
