"""Deterministic cash-flow forecaster."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from finsight.features.recurring_obligations import detect_recurring_patterns
from finsight.ingestion.schema import TransactionType, ValidatedTransaction


class HorizonForecast(BaseModel):
    horizon_days: int
    projected_balance: float
    expected_incoming: float
    expected_outgoing: float
    known_obligations: float
    discretionary_modeled: float
    is_shortfall: bool
    minimum_projected_balance: float


class CashflowForecastResult(BaseModel):
    account_id: str
    prediction_timestamp: datetime
    current_balance: float
    currency: str = "BDT"
    is_cold_start: bool = False
    data_quality_warning: Optional[str] = None
    horizons: Dict[int, HorizonForecast] = Field(default_factory=dict)
    daily_balance_trajectory: List[Dict[str, Any]] = Field(default_factory=list)


def forecast_deterministic_cashflow(
    history: List[ValidatedTransaction],
    current_balance: float,
    snapshot_dt: datetime,
    account_id: str = "DEFAULT",
    currency: str = "BDT",
    horizons: List[int] = [1, 3, 7, 14],
    safety_buffer: float = 500.0,
) -> CashflowForecastResult:
    """Project future balance trajectory deterministically up to 14 days."""
    past_txs = [tx for tx in history if tx.timestamp <= snapshot_dt]
    is_cold = len(past_txs) < 10

    # 1. Estimate average daily non-recurring discretionary spend from past 30 days
    t_30d = snapshot_dt - timedelta(days=30)
    discretionary_30d = [
        tx for tx in past_txs
        if tx.timestamp >= t_30d
        and tx.transaction_type == TransactionType.EXPENSE
        and not tx.is_recurring
        and not tx.is_internal_transfer
    ]
    total_disc = sum(tx.amount for tx in discretionary_30d)
    daily_discretionary = total_disc / 30.0 if not is_cold else 500.0  # conservative prior for cold start

    # 2. Detect recurring obligation patterns
    recurring_patterns = detect_recurring_patterns(past_txs, snapshot_dt)

    # 3. Detect regular income cadence (e.g. salary on 1st of month)
    incomes_30d = [
        tx for tx in past_txs
        if tx.timestamp >= t_30d
        and tx.transaction_type == TransactionType.INCOME
        and not tx.is_internal_transfer
    ]
    avg_income = sum(tx.amount for tx in incomes_30d) if incomes_30d else 0.0
    income_dom = incomes_30d[-1].timestamp.day if incomes_30d else None

    # Roll forward day by day up to max horizon
    max_horizon = max(horizons)
    trajectory = []
    sim_bal = current_balance

    daily_events = []
    for d in range(1, max_horizon + 1):
        future_day = snapshot_dt + timedelta(days=d)
        dom = future_day.day

        # Check for expected recurring bills on this day
        day_obligations = sum(
            pat.amount for pat in recurring_patterns if pat.day_of_month == dom
        )

        # Check for expected regular income on this day
        day_income = avg_income if (income_dom is not None and dom == income_dom) else 0.0

        # Discretionary spend
        day_spend = daily_discretionary + day_obligations
        sim_bal = sim_bal + day_income - day_spend

        trajectory.append({
            "day": d,
            "date": future_day.strftime("%Y-%m-%d"),
            "projected_balance": round(sim_bal, 2),
            "expected_income": round(day_income, 2),
            "expected_obligations": round(day_obligations, 2),
            "discretionary_spend": round(daily_discretionary, 2),
        })

    # Compile horizon summaries
    horizon_results: Dict[int, HorizonForecast] = {}
    for h in horizons:
        h_slice = trajectory[:h]
        final_bal = h_slice[-1]["projected_balance"]
        min_bal = min(x["projected_balance"] for x in h_slice)
        tot_inc = sum(x["expected_income"] for x in h_slice)
        tot_obl = sum(x["expected_obligations"] for x in h_slice)
        tot_disc = sum(x["discretionary_spend"] for x in h_slice)

        horizon_results[h] = HorizonForecast(
            horizon_days=h,
            projected_balance=final_bal,
            expected_incoming=tot_inc,
            expected_outgoing=tot_obl + tot_disc,
            known_obligations=tot_obl,
            discretionary_modeled=tot_disc,
            is_shortfall=min_bal < safety_buffer,
            minimum_projected_balance=min_bal,
        )

    warning = "INSUFFICIENT_HISTORY: Predictions based on bounded priors" if is_cold else None

    return CashflowForecastResult(
        account_id=account_id,
        prediction_timestamp=snapshot_dt,
        current_balance=current_balance,
        currency=currency,
        is_cold_start=is_cold,
        data_quality_warning=warning,
        horizons=horizon_results,
        daily_balance_trajectory=trajectory,
    )
