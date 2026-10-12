"""Transaction upload and data quality validation routes."""

import io
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from finsight.api.dependencies import enforce_rate_limit, get_current_user, get_db
from finsight.database.repositories import AccountRepository, TransactionRepository
from finsight.ingestion.csv_loader import load_transactions_from_csv
from finsight.ingestion.schema import DataQualityReport

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


@router.post("/upload", response_model=DataQualityReport)
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
