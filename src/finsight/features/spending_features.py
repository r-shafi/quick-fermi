"""Spending features computed strictly point-in-time."""

from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np

from finsight.ingestion.schema import (
    DISCRETIONARY_CATEGORIES,
    ESSENTIAL_CATEGORIES,
    TransactionCategory,
    TransactionType,
    ValidatedTransaction,
)


def extract_spending_features(
    history: List[ValidatedTransaction],
    snapshot_dt: datetime,
) -> Dict[str, float]:
    """Compute spending features using only transactions on or before snapshot_dt."""
    # Filter strictly to expenses on or before snapshot_dt
    expenses = [
        tx for tx in history
        if tx.timestamp <= snapshot_dt
        and tx.transaction_type == TransactionType.EXPENSE
        and not tx.is_internal_transfer
    ]

    t_7d = snapshot_dt - timedelta(days=7)
    t_30d = snapshot_dt - timedelta(days=30)
    t_90d = snapshot_dt - timedelta(days=90)

    spend_7d = sum(tx.amount for tx in expenses if tx.timestamp >= t_7d)
    spend_30d = sum(tx.amount for tx in expenses if tx.timestamp >= t_30d)
    spend_90d = sum(tx.amount for tx in expenses if tx.timestamp >= t_90d)

    freq_7d = sum(1 for tx in expenses if tx.timestamp >= t_7d)
    freq_30d = sum(1 for tx in expenses if tx.timestamp >= t_30d)
    freq_90d = sum(1 for tx in expenses if tx.timestamp >= t_90d)

    # Spending acceleration: daily rate over 7d vs daily rate over 30d
    rate_7d = spend_7d / 7.0
    rate_30d = spend_30d / 30.0
    epsilon = 1e-4
    spending_acceleration = rate_7d / (rate_30d + epsilon)

    # Rolling daily spending volatility over 30 days
    # Group spending by day
    daily_spend_map: Dict[str, float] = {}
    for d in range(30):
        day_date = (snapshot_dt - timedelta(days=d)).strftime("%Y-%m-%d")
        daily_spend_map[day_date] = 0.0

    for tx in expenses:
        if tx.timestamp >= t_30d:
            day_key = tx.timestamp.strftime("%Y-%m-%d")
            if day_key in daily_spend_map:
                daily_spend_map[day_key] += tx.amount

    daily_amounts = list(daily_spend_map.values())
    rolling_spend_volatility_30d = float(np.std(daily_amounts)) if len(daily_amounts) > 1 else 0.0

    # Categorization breakdown over 30d
    spend_30d_txs = [tx for tx in expenses if tx.timestamp >= t_30d]
    total_30d = sum(tx.amount for tx in spend_30d_txs)

    if total_30d > 0:
        essential_spend = sum(tx.amount for tx in spend_30d_txs if tx.is_essential)
        discretionary_spend = sum(tx.amount for tx in spend_30d_txs if tx.is_discretionary)
        uncertain_spend = sum(
            tx.amount for tx in spend_30d_txs
            if tx.category == TransactionCategory.UNCERTAIN
        )
        essential_ratio = essential_spend / total_30d
        discretionary_ratio = discretionary_spend / total_30d
        uncertain_ratio = uncertain_spend / total_30d
    else:
        essential_ratio = 0.0
        discretionary_ratio = 0.0
        uncertain_ratio = 0.0

    return {
        "spend_sum_7d": float(spend_7d),
        "spend_sum_30d": float(spend_30d),
        "spend_sum_90d": float(spend_90d),
        "spend_freq_7d": float(freq_7d),
        "spend_freq_30d": float(freq_30d),
        "spend_freq_90d": float(freq_90d),
        "spending_acceleration_7_vs_30": float(spending_acceleration),
        "rolling_spend_volatility_30d": float(rolling_spend_volatility_30d),
        "essential_spend_ratio_30d": float(essential_ratio),
        "discretionary_spend_ratio_30d": float(discretionary_ratio),
        "uncertain_category_ratio": float(uncertain_ratio),
    }
