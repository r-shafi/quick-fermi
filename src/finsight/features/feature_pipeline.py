"""Unified point-in-time financial feature pipeline."""

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from finsight.features.income_features import extract_income_features
from finsight.features.liquidity_features import extract_liquidity_features
from finsight.features.recurring_obligations import extract_recurring_features
from finsight.features.spending_features import extract_spending_features
from finsight.features.temporal_features import extract_temporal_features
from finsight.ingestion.schema import ValidatedTransaction

FEATURE_COLUMNS = [
    # Numerical
    "verified_available_balance",
    "income_sum_7d",
    "income_sum_30d",
    "income_sum_90d",
    "income_freq_30d",
    "spend_sum_7d",
    "spend_sum_30d",
    "spend_sum_90d",
    "spend_freq_30d",
    "spending_acceleration_7_vs_30",
    "net_cashflow_7d",
    "net_cashflow_30d",
    "known_recurring_bills_next_7d",
    "known_recurring_bills_next_14d",
    "days_to_next_major_bill",
    "rolling_spend_volatility_30d",
    "essential_spend_ratio_30d",
    "discretionary_spend_ratio_30d",
    "uncertain_category_ratio",
    "days_of_solvency",
    "history_days",
    "data_staleness_days",
    "data_completeness_score",
    "day_of_week",
    "day_of_month",
    # Binary
    "is_cold_start",
    "has_overdraft_facility",
    "is_sme_account",
]


def compute_point_in_time_features(
    history: List[ValidatedTransaction],
    snapshot_dt: datetime,
    current_balance: Optional[float] = None,
    is_sme: bool = False,
    has_overdraft: bool = False,
) -> Dict[str, float]:
    """Compute complete feature vector strictly at snapshot_dt.
    
    Guarantees no future lookahead leakage by filtering history <= snapshot_dt.
    """
    # Strict temporal isolation
    valid_history = [tx for tx in history if tx.timestamp <= snapshot_dt]

    feat = {}
    feat.update(extract_temporal_features(snapshot_dt))
    feat.update(extract_spending_features(valid_history, snapshot_dt))
    feat.update(extract_income_features(valid_history, snapshot_dt))
    feat.update(extract_recurring_features(valid_history, snapshot_dt))
    feat.update(
        extract_liquidity_features(
            valid_history,
            snapshot_dt,
            current_balance=current_balance,
            is_sme=is_sme,
            has_overdraft=has_overdraft,
        )
    )

    # Ensure all declared FEATURE_COLUMNS exist with float values
    ordered_features = {col: float(feat.get(col, 0.0)) for col in FEATURE_COLUMNS}
    return ordered_features


def generate_feature_dataset(
    transactions: List[ValidatedTransaction],
    snapshot_dates: List[datetime],
    account_id: str,
    is_sme: bool = False,
    has_overdraft: bool = False,
) -> pd.DataFrame:
    """Generate training/evaluation feature dataset across multiple temporal snapshots."""
    rows = []
    for dt in snapshot_dates:
        row = compute_point_in_time_features(
            transactions,
            snapshot_dt=dt,
            is_sme=is_sme,
            has_overdraft=has_overdraft,
        )
        row["account_id"] = account_id
        row["snapshot_timestamp"] = dt.isoformat()
        rows.append(row)

    return pd.DataFrame(rows)
