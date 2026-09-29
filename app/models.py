"""Data models for bank statement processing.

Defines the standard internal format that all extracted data
gets normalized into, regardless of the source bank or PDF type.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class ClassificationMethod(str, Enum):
    """How a transaction was classified."""
    RULE_BASED = "rule_based"
    ML_MODEL = "ml_model"
    UNCLASSIFIED = "unclassified"


class ValidationStatus(str, Enum):
    """Result of data validation checks."""
    VALID = "valid"
    WARNING = "warning"
    SUSPECT = "suspect"
    INVALID = "invalid"


@dataclass
class BankAccount:
    """Extracted account-level information from a bank statement."""
    bank_name: Optional[str] = None
    account_holder: Optional[str] = None
    account_number: Optional[str] = None
    ifsc: Optional[str] = None
    statement_period: Optional[str] = None


@dataclass
class Transaction:
    """A single financial transaction extracted from a statement."""
    date: Optional[date] = None
    description: str = ""
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None
    category: str = "Uncategorized"
    classification_method: ClassificationMethod = ClassificationMethod.UNCLASSIFIED
    confidence: float = 0.0
    needs_review: bool = False
    validation_status: ValidationStatus = ValidationStatus.VALID
    validation_notes: list[str] = field(default_factory=list)

    @property
    def review_status(self) -> str:
        """Human-readable review tag."""
        return "Needs Review" if self.needs_review else "Verified"


@dataclass
class ProcessingResult:
    """Complete result of processing a bank statement."""
    account: BankAccount = field(default_factory=BankAccount)
    transactions: list[Transaction] = field(default_factory=list)
    pdf_type: str = "unknown"  # "text" or "image"
    page_count: int = 0
    errors: list[str] = field(default_factory=list)
