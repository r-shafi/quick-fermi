"""Transaction upload, paginated query, and mathematical reconciliation routes."""

from datetime import datetime
import io
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from finsight.api.dependencies import enforce_rate_limit, get_current_user, get_db, verify_account_ownership
from finsight.database.models import AccountModel, TransactionModel
from finsight.database.repositories import AccountRepository, TransactionRepository
from finsight.ingestion.csv_loader import load_transactions_from_csv
from finsight.ingestion.schema import DataQualityReport

router = APIRouter(tags=["Transactions"])


class TransactionItemResponse(BaseModel):
    transaction_id: str
    account_id: str
    timestamp: str
    amount: float
    currency: str
    transaction_type: str
    category: str
    description: str
    counterparty: Optional[str] = None
    is_internal_transfer: bool = False
    is_recurring: bool = False
    balance_after: Optional[float] = None


class PaginatedTransactionsResponse(BaseModel):
    account_id: str
    total: int
    page: int
    page_size: int
    total_pages: int
    transactions: List[TransactionItemResponse]


class ReconciliationResponse(BaseModel):
    account_id: str
    opening_balance: float
    total_inflows: float
    total_outflows: float
    calculated_closing_balance: float
    recorded_closing_balance: float
    difference: float
    status: str  # RECONCILED, DISCREPANCY


@router.post("/api/v1/transactions/upload", response_model=DataQualityReport)
async def upload_transactions_csv(
    file: UploadFile = File(...),
    currency: str = Form("BDT"),
    account_type: str = Form("PERSONAL"),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Upload CSV transaction export, validate schema, deduplicate, and reconcile."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a CSV.",
        )

    content = await file.read()
    buffer = io.BytesIO(content)

    txs, report = load_transactions_from_csv(
        file_path_or_buffer=buffer,
        expected_currency=currency,
    )

    if report.has_unsupported_currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported currency mixing detected without FX rate. Expected {currency}.",
        )

    # Persist in DB
    if txs:
        acc_repo = AccountRepository(db)
        tx_repo = TransactionRepository(db)

        account_id = report.account_id
        # Calculate balance
        sorted_txs = sorted(txs, key=lambda x: x.timestamp)
        latest_bal = sorted_txs[-1].balance_after
        if latest_bal is None:
            latest_bal = sum(t.amount if t.transaction_type == "INCOME" else -t.amount for t in txs)

        acc_repo.upsert(
            account_id=account_id,
            account_type=account_type,
            currency=currency,
            available_balance=latest_bal,
            ledger_balance=latest_bal,
        )
        tx_repo.bulk_insert(txs)

    return report


@router.get("/api/v1/accounts/{account_id}/transactions", response_model=PaginatedTransactionsResponse)
def get_account_transactions(
    account_id: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tx_type: Optional[str] = Query(None, description="Filter by transaction type (INCOME, EXPENSE)"),
    search: Optional[str] = Query(None, description="Search description or counterparty"),
    date_from: Optional[str] = Query(None, description="ISO start date filter"),
    date_to: Optional[str] = Query(None, description="ISO end date filter"),
    user_id: str = Depends(verify_account_ownership),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve paginated transactions for an account with category, type, and date filtering."""
    query = db.query(TransactionModel).filter(TransactionModel.account_id == account_id)

    if category:
        query = query.filter(TransactionModel.category == category)

    if tx_type:
        query = query.filter(TransactionModel.transaction_type == tx_type)

    if search:
        search_like = f"%{search}%"
        query = query.filter(
            (TransactionModel.description.ilike(search_like))
            | (TransactionModel.counterparty.ilike(search_like))
        )

    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.filter(TransactionModel.timestamp >= dt_from)
        except ValueError:
            pass

    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.filter(TransactionModel.timestamp <= dt_to)
        except ValueError:
            pass

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size

    items = query.order_by(TransactionModel.timestamp.desc()).offset(offset).limit(page_size).all()

    tx_list = [
        TransactionItemResponse(
            transaction_id=t.transaction_id,
            account_id=t.account_id,
            timestamp=t.timestamp.isoformat(),
            amount=t.amount,
            currency=t.currency,
            transaction_type=t.transaction_type,
            category=t.category,
            description=t.description,
            counterparty=t.counterparty,
            is_internal_transfer=bool(t.is_internal_transfer),
            is_recurring=bool(t.is_recurring),
            balance_after=t.balance_after,
        )
        for t in items
    ]

    return PaginatedTransactionsResponse(
        account_id=account_id,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        transactions=tx_list,
    )


@router.get("/api/v1/accounts/{account_id}/reconciliation", response_model=ReconciliationResponse)
def get_account_reconciliation(
    account_id: str,
    user_id: str = Depends(verify_account_ownership),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Compute mathematical balance reconciliation verifying opening + inflows - outflows = closing."""
    acc_repo = AccountRepository(db)
    acc = acc_repo.get(account_id)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found.",
        )

    tx_repo = TransactionRepository(db)
    txs = tx_repo.list_by_account(account_id)

    if not txs:
        return ReconciliationResponse(
            account_id=account_id,
            opening_balance=round(acc.available_balance, 2),
            total_inflows=0.0,
            total_outflows=0.0,
            calculated_closing_balance=round(acc.available_balance, 2),
            recorded_closing_balance=round(acc.available_balance, 2),
            difference=0.0,
            status="RECONCILED",
        )

    sorted_txs = sorted(txs, key=lambda x: x.timestamp)

    # Determine opening balance from first transaction's balance_after if available
    first_tx = sorted_txs[0]
    if first_tx.balance_after is not None:
        if first_tx.transaction_type in ("INCOME", "REFUND", "REVERSAL"):
            opening_balance = round(first_tx.balance_after - first_tx.amount, 2)
        elif first_tx.transaction_type == "EXPENSE":
            opening_balance = round(first_tx.balance_after + first_tx.amount, 2)
        else:
            opening_balance = round(first_tx.balance_after, 2)
    else:
        opening_balance = 0.0

    total_inflows = round(
        sum(t.amount for t in sorted_txs if t.transaction_type in ("INCOME", "REFUND", "REVERSAL") and not t.is_internal_transfer),
        2,
    )
    total_outflows = round(
        sum(t.amount for t in sorted_txs if t.transaction_type == "EXPENSE" and not t.is_internal_transfer),
        2,
    )

    calculated_closing = round(opening_balance + total_inflows - total_outflows, 2)

    last_tx = sorted_txs[-1]
    recorded_closing = round(
        last_tx.balance_after if last_tx.balance_after is not None else acc.available_balance,
        2,
    )

    diff = round(abs(calculated_closing - recorded_closing), 2)
    recon_status = "RECONCILED" if diff <= 0.01 else "DISCREPANCY"

    return ReconciliationResponse(
        account_id=account_id,
        opening_balance=opening_balance,
        total_inflows=total_inflows,
        total_outflows=total_outflows,
        calculated_closing_balance=calculated_closing,
        recorded_closing_balance=recorded_closing,
        difference=diff,
        status=recon_status,
    )
