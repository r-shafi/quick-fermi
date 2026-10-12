"""Liquidity and solvency features computed strictly point-in-time."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from finsight.ingestion.schema import (
    TransactionType,
    ValidatedTransaction,
)


def extract_liquidity_features(
    history: List[ValidatedTransaction],
    snapshot_dt: datetime,
    current_balance: Optional[float] = None,
    is_sme: bool = False,
    has_overdraft: bool = False,
) -> Dict[str, float]:
    """Compute liquidity, solvency, and data completeness features."""
    past_txs = [tx for tx in history if tx.timestamp <= snapshot_dt]

    # If current_balance is not passed, infer from latest balance_after or calculate
    if current_balance is not None:
        balance = float(current_balance)
    elif past_txs and past_txs[-1].balance_after is not None:
        balance = float(past_txs[-1].balance_after)
    else:
        # Reconstruct from initial assumption
        balance = sum(
            (tx.amount if tx.transaction_type == TransactionType.INCOME else -tx.amount)
            for tx in past_txs if not tx.is_internal_transfer
        )

    t_7d = snapshot_dt - timedelta(days=7)
    t_30d = snapshot_dt - timedelta(days=30)

    # Net cash flow over 7d and 30d
    net_7d = 0.0
    net_30d = 0.0
    essential_spend_30d = 0.0

    for tx in past_txs:
        if tx.is_internal_transfer:
            continue

        delta = tx.amount if tx.transaction_type in (TransactionType.INCOME, TransactionType.REFUND) else -tx.amount

        if tx.timestamp >= t_7d:
            net_7d += delta
        if tx.timestamp >= t_30d:
            net_30d += delta
            if tx.transaction_type == TransactionType.EXPENSE and tx.is_essential:
                essential_spend_30d += tx.amount

    # Days of Solvency Calculation:
    # Documented formula: balance / (daily average essential spending over last 30d + epsilon)
    # If daily essential spend is zero or history < 7 days, bounded to 999.0
    avg_daily_essential_spend = essential_spend_30d / 30.0
    epsilon = 1e-4

    if balance <= 0:
        days_of_solvency = 0.0
    elif avg_daily_essential_spend > 0:
        days_of_solvency = min(999.0, balance / (avg_daily_essential_spend + epsilon))
    else:
        days_of_solvency = 999.0

    # History length and cold start flag
    if past_txs:
        earliest_dt = min(tx.timestamp for tx in past_txs)
        history_days = max(0.0, (snapshot_dt - earliest_dt).total_seconds() / 86400.0)
        latest_tx_dt = max(tx.timestamp for tx in past_txs)
        staleness_days = max(0.0, (snapshot_dt - latest_tx_dt).total_seconds() / 86400.0)
    else:
        history_days = 0.0
        staleness_days = 999.0

    is_cold_start = 1.0 if (history_days < 14.0 or len(past_txs) < 10) else 0.0
    completeness_score = 1.0 if not is_cold_start else max(0.1, history_days / 14.0)

    return {
        "verified_available_balance": float(balance),
        "net_cashflow_7d": float(net_7d),
        "net_cashflow_30d": float(net_30d),
        "days_of_solvency": float(days_of_solvency),
        "history_days": float(history_days),
        "data_staleness_days": float(staleness_days),
        "data_completeness_score": float(completeness_score),
        "is_cold_start": float(is_cold_start),
        "is_sme_account": 1.0 if is_sme else 0.0,
        "has_overdraft_facility": 1.0 if has_overdraft else 0.0,
    }
