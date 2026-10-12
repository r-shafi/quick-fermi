"""Recurring obligation detection and projection."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from finsight.ingestion.schema import (
    TransactionCategory,
    TransactionType,
    ValidatedTransaction,
)


class RecurringObligationPattern:
    def __init__(
        self,
        category: TransactionCategory,
        description: str,
        amount: float,
        cadence_days: int,
        day_of_month: int,
    ):
        self.category = category
        self.description = description
        self.amount = amount
        self.cadence_days = cadence_days
        self.day_of_month = day_of_month


def detect_recurring_patterns(
    history: List[ValidatedTransaction],
    snapshot_dt: datetime,
) -> List[RecurringObligationPattern]:
    """Detect recurring obligation patterns based only on history up to snapshot_dt."""
    # Look for recurring expenses or transactions marked is_recurring
    patterns: List[RecurringObligationPattern] = []

    # Map by category
    cat_expenses: Dict[TransactionCategory, List[ValidatedTransaction]] = {}
    for tx in history:
        if tx.timestamp <= snapshot_dt and tx.transaction_type == TransactionType.EXPENSE:
            cat_expenses.setdefault(tx.category, []).append(tx)

    # Detect monthly bills: Rent, Utilities, Payroll, Debt Repayment
    for cat, txs in cat_expenses.items():
        if cat in (
            TransactionCategory.RENT,
            TransactionCategory.MORTGAGE,
            TransactionCategory.UTILITIES,
            TransactionCategory.PAYROLL,
            TransactionCategory.DEBT_REPAYMENT,
        ) or any(tx.is_recurring for tx in txs):
            if txs:
                avg_amt = sum(t.amount for t in txs) / len(txs)
                # Most recent occurrence day of month
                latest = max(txs, key=lambda t: t.timestamp)
                dom = latest.timestamp.day
                patterns.append(
                    RecurringObligationPattern(
                        category=cat,
                        description=latest.description or cat.value,
                        amount=avg_amt,
                        cadence_days=30,
                        day_of_month=dom,
                    )
                )

    return patterns


def extract_recurring_features(
    history: List[ValidatedTransaction],
    snapshot_dt: datetime,
) -> Dict[str, float]:
    """Extract upcoming recurring obligations for the next 7 and 14 days."""
    patterns = detect_recurring_patterns(history, snapshot_dt)

    bills_next_7d = 0.0
    bills_next_14d = 0.0
    min_days_to_bill = 999.0

    current_dom = snapshot_dt.day

    for pat in patterns:
        # Calculate days until next occurrence of day_of_month
        if pat.day_of_month >= current_dom:
            days_ahead = pat.day_of_month - current_dom
        else:
            # Next month (assume ~30 days in month)
            days_ahead = (30 - current_dom) + pat.day_of_month

        if days_ahead < min_days_to_bill:
            min_days_to_bill = float(days_ahead)

        if days_ahead <= 7:
            bills_next_7d += pat.amount
        if days_ahead <= 14:
            bills_next_14d += pat.amount

    return {
        "known_recurring_bills_next_7d": float(bills_next_7d),
        "known_recurring_bills_next_14d": float(bills_next_14d),
        "days_to_next_major_bill": float(min_days_to_bill),
    }
