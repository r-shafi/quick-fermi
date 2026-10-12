"""Data models and schemas for transaction ingestion and validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TransactionType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"
    REFUND = "REFUND"
    REVERSAL = "REVERSAL"
    PENDING = "PENDING"


class AccountType(str, Enum):
    PERSONAL = "PERSONAL"
    SME = "SME"


class TransactionCategory(str, Enum):
    SALARY = "SALARY"
    INVOICE_RECEIPT = "INVOICE_RECEIPT"
    INVESTMENT_INCOME = "INVESTMENT_INCOME"
    RENT = "RENT"
    MORTGAGE = "MORTGAGE"
    UTILITIES = "UTILITIES"
    HEALTHCARE = "HEALTHCARE"
    DEBT_REPAYMENT = "DEBT_REPAYMENT"
    GROCERIES = "GROCERIES"
    PAYROLL = "PAYROLL"
    SUPPLIER = "SUPPLIER"
    TAX = "TAX"
    ENTERTAINMENT = "ENTERTAINMENT"
    DINING = "DINING"
    SHOPPING = "SHOPPING"
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"
    UNCERTAIN = "UNCERTAIN"


# Essential categories that must NEVER be suggested for cancellation or pause
ESSENTIAL_CATEGORIES = {
    TransactionCategory.RENT,
    TransactionCategory.MORTGAGE,
    TransactionCategory.UTILITIES,
    TransactionCategory.HEALTHCARE,
    TransactionCategory.DEBT_REPAYMENT,
    TransactionCategory.PAYROLL,
    TransactionCategory.TAX,
}

DISCRETIONARY_CATEGORIES = {
    TransactionCategory.ENTERTAINMENT,
    TransactionCategory.DINING,
    TransactionCategory.SHOPPING,
}


class RawTransaction(BaseModel):
    transaction_id: str
    account_id: str
    timestamp: str  # ISO string or date
    amount: float
    currency: str = "BDT"
    transaction_type: str = "EXPENSE"
    category: Optional[str] = "UNCERTAIN"
    description: Optional[str] = ""
    counterparty: Optional[str] = None
    is_internal_transfer: bool = False
    is_recurring: bool = False
    balance_after: Optional[float] = None


class ValidatedTransaction(BaseModel):
    transaction_id: str
    account_id: str
    timestamp: datetime
    amount: float
    currency: str
    transaction_type: TransactionType
    category: TransactionCategory
    description: str = ""
    counterparty: Optional[str] = None
    is_internal_transfer: bool = False
    is_recurring: bool = False
    balance_after: Optional[float] = None
    is_essential: bool = False
    is_discretionary: bool = False


class AccountSnapshot(BaseModel):
    account_id: str
    account_type: AccountType = AccountType.PERSONAL
    currency: str = "BDT"
    available_balance: float
    ledger_balance: float
    credit_limit: float = 0.0
    as_of: datetime
    has_overdraft_facility: bool = False


class DataQualityIssue(BaseModel):
    level: str = "WARNING"  # WARNING, ERROR, CRITICAL
    issue_type: str
    message: str
    row_index: Optional[int] = None
    transaction_id: Optional[str] = None


class DataQualityReport(BaseModel):
    account_id: str
    total_records: int
    valid_records: int
    duplicate_records: int
    rejected_records: int
    issues: List[DataQualityIssue] = Field(default_factory=list)
    reconciled: bool = False
    reconciliation_discrepancy: float = 0.0
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    data_completeness_score: float = 1.0  # 0.0 to 1.0
    staleness_days: float = 0.0
    history_days: float = 0.0
    currency: str = "BDT"
    has_unsupported_currency: bool = False
