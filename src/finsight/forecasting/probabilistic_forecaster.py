"""Probabilistic cash-flow forecaster with uncertainty bounds."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field

from finsight.features.recurring_obligations import detect_recurring_patterns
from finsight.forecasting.deterministic_cashflow import HorizonForecast
from finsight.ingestion.schema import TransactionType, ValidatedTransaction


class ProbabilisticHorizonForecast(BaseModel):
    horizon_days: int
    projected_balance_median: float
    lower_bound_p10: float
    upper_bound_p90: float
    interval_width: float
    probability_shortfall: float
    expected_incoming: float
    expected_outgoing: float
    known_obligations: float


class ProbabilisticCashflowResult(BaseModel):
    account_id: str
    prediction_timestamp: datetime
    current_balance: float
    currency: str = "BDT"
    is_cold_start: bool = False
    horizons: Dict[int, ProbabilisticHorizonForecast] = Field(default_factory=dict)
    daily_intervals: List[Dict[str, Any]] = Field(default_factory=list)


def forecast_probabilistic_cashflow(
    history: List[ValidatedTransaction],
    current_balance: float,
    snapshot_dt: datetime,
    account_id: str = "DEFAULT",
    currency: str = "BDT",
    horizons: List[int] = [1, 3, 7, 14],
    safety_buffer: float = 500.0,
    n_simulations: int = 500,
) -> ProbabilisticCashflowResult:
    """Simulate future cash-flow paths and generate 10th, 50th, 90th percentile bounds."""
    past_txs = [tx for tx in history if tx.timestamp <= snapshot_dt]
    is_cold = len(past_txs) < 10

    # 1. Historical daily net cashflow residuals (excluding known recurring items)
    recurring_patterns = detect_recurring_patterns(past_txs, snapshot_dt)
    
    # Collect daily non-recurring cash flows over past 60 days
    t_60d = snapshot_dt - timedelta(days=60)
    non_recurring_txs = [
        tx for tx in past_txs
        if tx.timestamp >= t_60d
        and not tx.is_recurring
        and not tx.is_internal_transfer
    ]

    daily_residuals: List[float] = []
    days_checked = min(60, max(1, int((snapshot_dt - (past_txs[0].timestamp if past_txs else snapshot_dt)).days)))
    for d in range(days_checked):
        day_date = (snapshot_dt - timedelta(days=d)).date()
        day_net = sum(
            (t.amount if t.transaction_type == TransactionType.INCOME else -t.amount)
            for t in non_recurring_txs
            if t.timestamp.date() == day_date
        )
        daily_residuals.append(day_net)

    if not daily_residuals or is_cold:
        daily_residuals = [-800.0, -500.0, -200.0, -100.0, 0.0, 500.0]

    res_arr = np.array(daily_residuals)
    res_mean = float(np.mean(res_arr))
    res_std = max(100.0, float(np.std(res_arr)))

    max_h = max(horizons)
    # Monte Carlo simulation of residual daily drift
    sim_paths = np.zeros((n_simulations, max_h))
    
    # Compute deterministic recurring base per day
    daily_obligations = []
    for d in range(1, max_h + 1):
        future_day = snapshot_dt + timedelta(days=d)
        dom = future_day.day
        day_obl = sum(pat.amount for pat in recurring_patterns if pat.day_of_month == dom)
        daily_obligations.append(day_obl)

    rng = np.random.default_rng(42)
    for i in range(n_simulations):
        bal = current_balance
        for d in range(max_h):
            # Sample daily non-recurring shock
            shock = rng.normal(res_mean, res_std)
            bal = bal - daily_obligations[d] + shock
            sim_paths[i, d] = bal

    # Daily quantiles
    daily_intervals = []
    for d in range(max_h):
        day_vals = sim_paths[:, d]
        p10 = float(np.percentile(day_vals, 10))
        p50 = float(np.percentile(day_vals, 50))
        p90 = float(np.percentile(day_vals, 90))
        future_dt = snapshot_dt + timedelta(days=d + 1)
        daily_intervals.append({
            "day": d + 1,
            "date": future_dt.strftime("%Y-%m-%d"),
            "lower_p10": round(p10, 2),
            "median_p50": round(p50, 2),
            "upper_p90": round(p90, 2),
            "known_obligations": round(daily_obligations[d], 2),
        })

    # Horizon aggregates
    horizon_results: Dict[int, ProbabilisticHorizonForecast] = {}
    for h in horizons:
        h_idx = h - 1
        p10 = float(np.percentile(sim_paths[:, h_idx], 10))
        p50 = float(np.percentile(sim_paths[:, h_idx], 50))
        p90 = float(np.percentile(sim_paths[:, h_idx], 90))
        # Shortfall probability: fraction of paths that breached safety buffer at ANY point up to h
        path_mins = np.min(sim_paths[:, :h], axis=1)
        prob_shortfall = float(np.mean(path_mins < safety_buffer))

        tot_obl = sum(daily_obligations[:h])

        horizon_results[h] = ProbabilisticHorizonForecast(
            horizon_days=h,
            projected_balance_median=round(p50, 2),
            lower_bound_p10=round(p10, 2),
            upper_bound_p90=round(p90, 2),
            interval_width=round(p90 - p10, 2),
            probability_shortfall=round(prob_shortfall, 4),
            expected_incoming=0.0,
            expected_outgoing=round(tot_obl + abs(res_mean * h), 2),
            known_obligations=round(tot_obl, 2),
        )

    return ProbabilisticCashflowResult(
        account_id=account_id,
        prediction_timestamp=snapshot_dt,
        current_balance=current_balance,
        currency=currency,
        is_cold_start=is_cold,
        horizons=horizon_results,
        daily_intervals=daily_intervals,
    )
