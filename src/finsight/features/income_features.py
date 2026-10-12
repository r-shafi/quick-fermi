"""Income features computed strictly point-in-time."""

from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np

from finsight.ingestion.schema import (
    TransactionType,
    ValidatedTransaction,
)


def extract_income_features(
    history: List[ValidatedTransaction],
    snapshot_dt: datetime,
) -> Dict[str, float]:
    """Compute income metrics using only transactions on or before snapshot_dt."""
    incomes = [
        tx for tx in history
        if tx.timestamp <= snapshot_dt
        and tx.transaction_type in (TransactionType.INCOME, TransactionType.REFUND)
        and not tx.is_internal_transfer
    ]

    t_7d = snapshot_dt - timedelta(days=7)
    t_30d = snapshot_dt - timedelta(days=30)
    t_90d = snapshot_dt - timedelta(days=90)

    income_7d = sum(tx.amount for tx in incomes if tx.timestamp >= t_7d)
    income_30d = sum(tx.amount for tx in incomes if tx.timestamp >= t_30d)
    income_90d = sum(tx.amount for tx in incomes if tx.timestamp >= t_90d)

    freq_30d = sum(1 for tx in incomes if tx.timestamp >= t_30d)

    # Days since last income
    if incomes:
        latest_income = max(incomes, key=lambda x: x.timestamp)
        days_since_last_income = max(
            0.0, (snapshot_dt - latest_income.timestamp).total_seconds() / 86400.0
        )
    else:
        days_since_last_income = 999.0

    # Income regularity: check intervals between historical incomes
    if len(incomes) >= 2:
        sorted_incomes = sorted(incomes, key=lambda x: x.timestamp)
        intervals = [
            (sorted_incomes[i].timestamp - sorted_incomes[i - 1].timestamp).total_seconds() / 86400.0
            for i in range(1, len(sorted_incomes))
        ]
        mean_interval = float(np.mean(intervals))
        std_interval = float(np.std(intervals))
        # Estimate days to next income
        estimated_next_income_days = max(1.0, mean_interval - days_since_last_income)
    else:
        mean_interval = 30.0
        std_interval = 0.0
        estimated_next_income_days = 30.0

    return {
        "income_sum_7d": float(income_7d),
        "income_sum_30d": float(income_30d),
        "income_sum_90d": float(income_90d),
        "income_freq_30d": float(freq_30d),
        "days_since_last_income": float(days_since_last_income),
        "estimated_next_income_days": float(estimated_next_income_days),
        "income_interval_regularity": float(std_interval),
    }
