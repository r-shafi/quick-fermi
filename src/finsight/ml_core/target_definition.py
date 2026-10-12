"""Target definitions and label construction for cash shortfall prediction."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import pandas as pd


class ShortfallOutcomeType(str, Enum):
    OBSERVED_LOW_BALANCE = "OBSERVED_LOW_BALANCE"
    ACTUAL_DECLINED_PAYMENT = "ACTUAL_DECLINED_PAYMENT"
    ACTUAL_OVERDRAFT = "ACTUAL_OVERDRAFT"
    ACTUAL_FINANCIAL_LOSS = "ACTUAL_FINANCIAL_LOSS"
    FORECASTED_LOW_BALANCE = "FORECASTED_LOW_BALANCE"


class TargetDefinition:
    """Documented cash shortfall target definition."""

    VERSION = "1.0.0"

    def __init__(
        self,
        horizon_days: int = 7,
        minimum_safety_balance: float = 500.0,
        include_overdraft: bool = False,
        overdraft_limit: float = 0.0,
    ):
        self.horizon_days = horizon_days
        self.minimum_safety_balance = minimum_safety_balance
        self.include_overdraft = include_overdraft
        self.overdraft_limit = overdraft_limit

    @property
    def target_name(self) -> str:
        return f"shortfall_within_{self.horizon_days}_days"

    def compute_label(
        self,
        snapshot_dt: datetime,
        ground_truth_df: pd.DataFrame,
        account_id: str,
    ) -> Tuple[Optional[int], Optional[float], ShortfallOutcomeType]:
        """Compute ground-truth label for a snapshot date using simulation ground truth.
        
        Returns:
            (label, min_balance_observed, outcome_type)
            label is None if future observation window is incomplete (censored).
        """
        # Filter ground truth for account
        acc_gt = ground_truth_df[ground_truth_df["account_id"] == account_id].copy()
        if acc_gt.empty:
            return None, None, ShortfallOutcomeType.OBSERVED_LOW_BALANCE

        acc_gt["date"] = pd.to_datetime(acc_gt["date"])
        # Snapshot date truncated to calendar day
        snap_date = pd.to_datetime(snapshot_dt.strftime("%Y-%m-%d"))
        window_end_date = snap_date + timedelta(days=self.horizon_days)

        # Check if future window is fully observed
        max_obs_date = acc_gt["date"].max()
        if window_end_date > max_obs_date:
            # Incomplete future observation window (censored sample)
            return None, None, ShortfallOutcomeType.OBSERVED_LOW_BALANCE

        # Window: (snap_date, window_end_date]
        window_gt = acc_gt[(acc_gt["date"] > snap_date) & (acc_gt["date"] <= window_end_date)]
        if window_gt.empty:
            return None, None, ShortfallOutcomeType.OBSERVED_LOW_BALANCE

        min_bal = float(window_gt["ending_balance"].min())

        effective_threshold = self.minimum_safety_balance
        if self.include_overdraft:
            effective_threshold -= self.overdraft_limit

        is_shortfall = 1 if min_bal < effective_threshold else 0

        if min_bal < 0:
            outcome = ShortfallOutcomeType.ACTUAL_OVERDRAFT
        elif is_shortfall:
            outcome = ShortfallOutcomeType.OBSERVED_LOW_BALANCE
        else:
            outcome = ShortfallOutcomeType.OBSERVED_LOW_BALANCE

        return is_shortfall, min_bal, outcome
