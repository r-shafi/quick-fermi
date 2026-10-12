"""Account summary and state routes."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from finsight.api.dependencies import enforce_rate_limit, get_current_user, get_db, verify_account_ownership
from finsight.database.repositories import AccountRepository, TransactionRepository

router = APIRouter(prefix="/api/v1/accounts", tags=["Accounts"])


class AccountSummaryResponse(BaseModel):
    account_id: str
    account_type: str
    currency: str
    available_balance: float
    ledger_balance: float
    credit_limit: float
    has_overdraft: bool
    total_transactions: int
    history_days: float
    data_staleness_days: float
    is_cold_start: bool
    last_updated: Optional[datetime] = None


@router.get("", response_model=List[AccountSummaryResponse])
def list_accounts(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """List all accounts accessible by the caller."""
    acc_repo = AccountRepository(db)
    accounts = acc_repo.get_all()
    results = []

    for acc in accounts:
        # Check authorization
        try:
            from finsight.security.authorization import auth_manager
            auth_manager.verify_account_access(user_id=user_id, account_id=acc.account_id)
        except Exception:
            continue

        tx_repo = TransactionRepository(db)
        txs = tx_repo.list_by_account(acc.account_id)
        n_tx = len(txs)

        hist_days = 0.0
        staleness_days = 0.0
        if txs:
            now_dt = datetime.utcnow()
            earliest = txs[0].timestamp
            latest = txs[-1].timestamp
            hist_days = max(0.0, (latest - earliest).total_seconds() / 86400.0)
            staleness_days = max(0.0, (now_dt - latest).total_seconds() / 86400.0)

        results.append(
            AccountSummaryResponse(
                account_id=acc.account_id,
                account_type=acc.account_type,
                currency=acc.currency,
                available_balance=acc.available_balance,
                ledger_balance=acc.ledger_balance,
                credit_limit=acc.credit_limit,
                has_overdraft=acc.has_overdraft,
                total_transactions=n_tx,
                history_days=round(hist_days, 1),
                data_staleness_days=round(staleness_days, 1),
                is_cold_start=(hist_days < 14.0 or n_tx < 10),
                last_updated=acc.updated_at,
            )
        )
    return results


@router.get("/{account_id}/summary", response_model=AccountSummaryResponse)
def get_account_summary(
    account_id: str,
    user_id: str = Depends(verify_account_ownership),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve detailed financial and data quality summary for a specific account."""
    acc_repo = AccountRepository(db)
    acc = acc_repo.get(account_id)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found.",
        )

    tx_repo = TransactionRepository(db)
    txs = tx_repo.list_by_account(account_id)
    n_tx = len(txs)

    hist_days = 0.0
    staleness_days = 0.0
    if txs:
        now_dt = datetime.utcnow()
        earliest = txs[0].timestamp
        latest = txs[-1].timestamp
        hist_days = max(0.0, (latest - earliest).total_seconds() / 86400.0)
        staleness_days = max(0.0, (now_dt - latest).total_seconds() / 86400.0)

    return AccountSummaryResponse(
        account_id=acc.account_id,
        account_type=acc.account_type,
        currency=acc.currency,
        available_balance=acc.available_balance,
        ledger_balance=acc.ledger_balance,
        credit_limit=acc.credit_limit,
        has_overdraft=acc.has_overdraft,
        total_transactions=n_tx,
        history_days=round(hist_days, 1),
        data_staleness_days=round(staleness_days, 1),
        is_cold_start=(hist_days < 14.0 or n_tx < 10),
        last_updated=acc.updated_at,
    )
