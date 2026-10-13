"""Scenario simulation and stress-testing API endpoints."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from finsight.api.dependencies import enforce_rate_limit, get_db, verify_account_ownership
from finsight.api.routes.forecasts import _to_validated_transactions
from finsight.database.repositories import AccountRepository, TransactionRepository
from finsight.forecasting.deterministic_cashflow import forecast_deterministic_cashflow
from finsight.ingestion.schema import (
    DISCRETIONARY_CATEGORIES,
    ESSENTIAL_CATEGORIES,
    TransactionCategory,
    TransactionType,
)

router = APIRouter(prefix="/api/v1/accounts", tags=["Scenario Simulation"])


class ScenarioAssumptionRequest(BaseModel):
    delayed_receipt_days: int = Field(0, description="Shift incoming receipts forward by N days")
    receipt_amount_factor: float = Field(1.0, ge=0.0, le=5.0, description="Multiplier for income receipts (e.g. 0.8 for 20% haircut)")
    supplier_invoice_factor: float = Field(1.0, ge=0.0, le=5.0, description="Multiplier for supplier expenses")
    payroll_date_offset: int = Field(0, description="Offset payroll schedule by N days")
    discretionary_expense_factor: float = Field(1.0, ge=0.0, le=5.0, description="Multiplier for discretionary expenditures")


class ScenarioComparison(BaseModel):
    lowest_balance: float
    threshold_crossing_day: Optional[int] = None
    net_change_bdt: float


class ScenarioResponse(BaseModel):
    account_id: str
    scenario_label: str
    simulation_mode: bool = True
    modified_assumptions: Dict[str, Any]
    baseline_forecast: Dict[str, Any]
    scenario_forecast: Dict[str, Any]
    comparison: ScenarioComparison


@router.post("/{account_id}/scenario", response_model=ScenarioResponse)
def simulate_account_scenario(
    account_id: str,
    assumptions: ScenarioAssumptionRequest = ScenarioAssumptionRequest(),
    user_id: str = Depends(verify_account_ownership),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Run deterministic cash-flow forecasting under user-modified stress assumptions."""
    acc_repo = AccountRepository(db)
    acc = acc_repo.get(account_id)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found.",
        )

    tx_repo = TransactionRepository(db)
    db_txs = tx_repo.list_by_account(account_id)
    raw_txs = _to_validated_transactions(db_txs)

    now_dt = datetime.now(ZoneInfo("Asia/Dhaka"))

    # 1. Baseline deterministic forecast
    baseline = forecast_deterministic_cashflow(
        history=raw_txs,
        current_balance=acc.available_balance,
        snapshot_dt=now_dt,
        account_id=account_id,
        currency=acc.currency,
    )

    # 2. Build modified scenario transactions
    modified_txs = []
    for tx in raw_txs:
        mod_tx = tx.model_copy(deep=True)

        if mod_tx.transaction_type == TransactionType.INCOME:
            mod_tx.amount = round(mod_tx.amount * assumptions.receipt_amount_factor, 2)
            if assumptions.delayed_receipt_days != 0:
                mod_tx.timestamp = mod_tx.timestamp + timedelta(days=assumptions.delayed_receipt_days)

        elif mod_tx.transaction_type == TransactionType.EXPENSE:
            if mod_tx.category == TransactionCategory.SUPPLIER:
                mod_tx.amount = round(mod_tx.amount * assumptions.supplier_invoice_factor, 2)
            elif mod_tx.category == TransactionCategory.PAYROLL:
                if assumptions.payroll_date_offset != 0:
                    mod_tx.timestamp = mod_tx.timestamp + timedelta(days=assumptions.payroll_date_offset)
            elif mod_tx.category in DISCRETIONARY_CATEGORIES or (
                not mod_tx.is_recurring and mod_tx.category not in ESSENTIAL_CATEGORIES
            ):
                mod_tx.amount = round(mod_tx.amount * assumptions.discretionary_expense_factor, 2)

        modified_txs.append(mod_tx)

    # 3. Scenario deterministic forecast
    scenario = forecast_deterministic_cashflow(
        history=modified_txs,
        current_balance=acc.available_balance,
        snapshot_dt=now_dt,
        account_id=account_id,
        currency=acc.currency,
    )

    # 4. Compute comparative metrics
    scenario_traj = scenario.daily_balance_trajectory
    baseline_traj = baseline.daily_balance_trajectory

    lowest_balance = min((d["projected_balance"] for d in scenario_traj), default=acc.available_balance)

    safety_buffer = 500.0 if acc.currency == "BDT" else 50.0
    threshold_crossing_day = None
    for d in scenario_traj:
        if d["projected_balance"] < safety_buffer:
            threshold_crossing_day = d["day"]
            break

    net_change = 0.0
    if scenario_traj and baseline_traj:
        net_change = round(scenario_traj[-1]["projected_balance"] - baseline_traj[-1]["projected_balance"], 2)

    scenario_label = (
        f"[SIMULATED] Scenario: Income {assumptions.receipt_amount_factor * 100:.0f}%, "
        f"Delay +{assumptions.delayed_receipt_days}d, Supplier {assumptions.supplier_invoice_factor * 100:.0f}%, "
        f"Disc {assumptions.discretionary_expense_factor * 100:.0f}%"
    )

    return ScenarioResponse(
        account_id=account_id,
        scenario_label=scenario_label,
        simulation_mode=True,
        modified_assumptions=assumptions.model_dump(),
        baseline_forecast=baseline.model_dump(),
        scenario_forecast=scenario.model_dump(),
        comparison=ScenarioComparison(
            lowest_balance=round(lowest_balance, 2),
            threshold_crossing_day=threshold_crossing_day,
            net_change_bdt=net_change,
        ),
    )
