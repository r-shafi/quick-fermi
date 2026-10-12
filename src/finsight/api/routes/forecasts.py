"""Cash-flow forecasting API endpoints."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from finsight.api.dependencies import enforce_rate_limit, get_db, verify_account_ownership
from finsight.database.repositories import AccountRepository, TransactionRepository
from finsight.forecasting.deterministic_cashflow import forecast_deterministic_cashflow
from finsight.forecasting.probabilistic_forecaster import forecast_probabilistic_cashflow
from finsight.ingestion.schema import TransactionCategory, TransactionType, ValidatedTransaction

router = APIRouter(prefix="/api/v1/accounts", tags=["Forecasts"])


def _to_validated_transactions(db_txs) -> list:
    results = []
    for t in db_txs:
        # Map category safely
        cat = TransactionCategory.UNCERTAIN
        try:
            cat = TransactionCategory(t.category)
        except Exception:
            pass

        results.append(
            ValidatedTransaction(
                transaction_id=t.transaction_id,
                account_id=t.account_id,
                timestamp=t.timestamp.replace(tzinfo=ZoneInfo("Asia/Dhaka")),
                amount=t.amount,
                currency=t.currency,
                transaction_type=TransactionType(t.transaction_type),
                category=cat,
                description=t.description or "",
                counterparty=t.counterparty,
                is_internal_transfer=t.is_internal_transfer,
                is_recurring=t.is_recurring,
                balance_after=t.balance_after,
            )
        )
    return results


@router.get("/{account_id}/forecast")
def get_account_forecast(
    account_id: str,
    method: str = Query("probabilistic", enum=["deterministic", "probabilistic"]),
    user_id: str = Depends(verify_account_ownership),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve 1, 3, 7, and 14-day cash-flow forecasts with uncertainty intervals."""
    acc_repo = AccountRepository(db)
    acc = acc_repo.get(account_id)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found.",
        )

    tx_repo = TransactionRepository(db)
    db_txs = tx_repo.list_by_account(account_id)
    txs = _to_validated_transactions(db_txs)

    now_dt = datetime.now(ZoneInfo("Asia/Dhaka"))

    if method == "deterministic":
        result = forecast_deterministic_cashflow(
            history=txs,
            current_balance=acc.available_balance,
            snapshot_dt=now_dt,
            account_id=account_id,
            currency=acc.currency,
        )
        return result.model_dump()
    else:
        result = forecast_probabilistic_cashflow(
            history=txs,
            current_balance=acc.available_balance,
            snapshot_dt=now_dt,
            account_id=account_id,
            currency=acc.currency,
        )
        return result.model_dump()
