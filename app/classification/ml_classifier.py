"""Machine Learning Transaction Classifier (Non-LLM).

Pipeline:
    Transaction Description
             ↓
        Text Cleaning
             ↓
           TF-IDF
             ↓
    Logistic Regression
             ↓
     Category + Confidence

Uses scikit-learn and joblib for model persistence at `models/classifier.pkl`.
"""

import os
import re
from typing import List, Optional, Tuple
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.models import Transaction, ClassificationMethod


DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "models",
    "classifier.pkl",
)
DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "train_transactions.csv",
)

_cached_model: Optional[Pipeline] = None


def clean_text_for_ml(text: str) -> str:
    """Preprocess transaction description for ML vectorization.

    - Convert to lower case
    - Remove punctuation and symbols (keeping alphanumeric and whitespace)
    - Collapse redundant spaces
    """
    if not text:
        return ""

    text = str(text).lower()
    # Replace non-alphanumeric chars with space
    text = re.sub(r"[^\w\s]", " ", text)
    # Replace numbers with a generic token to preserve patterns without overfitting
    text = re.sub(r"\b\d+\b", " ", text)
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_pipeline() -> Pipeline:
    """Create the TF-IDF + Logistic Regression classification pipeline."""
    return Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                sublinear_tf=True,
                max_features=5000,
            ),
        ),
        (
            "clf",
            LogisticRegression(
                C=5.0,
                max_iter=1000,
                random_state=42,
            ),
        ),
    ])


def train_model(
    data_path: str = DEFAULT_DATA_PATH,
    model_save_path: str = DEFAULT_MODEL_PATH,
) -> Pipeline:
    """Train the TF-IDF + Logistic Regression model from CSV data and save with joblib.

    Args:
        data_path: Path to CSV with columns ['description', 'category'].
        model_save_path: Destination path for serialized .pkl model.

    Returns:
        The trained Pipeline.
    """
    df = pd.read_csv(data_path)
    if "description" not in df.columns or "category" not in df.columns:
        raise ValueError("Training dataset must contain 'description' and 'category' columns")

    # Clean text
    x_clean = [clean_text_for_ml(d) for d in df["description"]]
    y = df["category"]

    pipeline = build_pipeline()
    pipeline.fit(x_clean, y)

    # Ensure models directory exists
    os.makedirs(os.path.dirname(model_save_path), exist_ok=True)
    joblib.dump(pipeline, model_save_path)

    global _cached_model
    _cached_model = pipeline
    return pipeline


def load_model(model_path: str = DEFAULT_MODEL_PATH) -> Pipeline:
    """Load the trained ML model from disk using joblib.

    Caches the model in memory for fast inference.
    """
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    if not os.path.exists(model_path):
        # Auto-train if not yet trained
        if os.path.exists(DEFAULT_DATA_PATH):
            return train_model(DEFAULT_DATA_PATH, model_path)
        raise FileNotFoundError(f"Model file not found at {model_path} and training data not found.")

    _cached_model = joblib.load(model_path)
    return _cached_model


def predict_text(
    description: str,
    model: Optional[Pipeline] = None,
    min_confidence: float = 0.12,
) -> Tuple[str, float]:
    """Predict category and confidence score for a single description string.

    Args:
        description: Raw transaction description text.
        model: Trained Pipeline (if None, loaded from disk).
        min_confidence: Minimum probability to assign a specific category.

    Returns:
        Tuple of (predicted_category, confidence_probability).
    """
    if model is None:
        model = load_model()

    cleaned = clean_text_for_ml(description)
    if not cleaned:
        return "Other", 0.0

    probas = model.predict_proba([cleaned])[0]
    max_idx = probas.argmax()
    confidence = float(probas[max_idx])
    category = model.classes_[max_idx]

    if confidence < min_confidence:
        return "Other", confidence

    return category, confidence


def classify_with_ml(
    transactions: List[Transaction],
    model: Optional[Pipeline] = None,
    only_unclassified: bool = True,
) -> List[Transaction]:
    """Apply the ML classifier to transactions.

    Args:
        transactions: List of Transaction models.
        model: Trained pipeline.
        only_unclassified: If True, only classifies items not already classified
                           by rule-based heuristics.

    Returns:
        Transactions with assigned categories and confidence scores.
    """
    if model is None:
        model = load_model()

    for txn in transactions:
        if only_unclassified and txn.classification_method != ClassificationMethod.UNCLASSIFIED:
            continue

        cat, conf = predict_text(txn.description, model=model)
        txn.category = cat
        txn.classification_method = ClassificationMethod.ML_MODEL
        txn.confidence = round(conf, 4)

    return transactions
