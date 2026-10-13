"""Data quality auditing, dry-run CSV validation, and synthetic profiles routes."""

from collections import Counter
from datetime import datetime
import io
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from finsight.api.dependencies import enforce_rate_limit, get_current_user, get_db, verify_account_ownership
from finsight.config import PROJECT_ROOT
from finsight.database.repositories import AccountRepository, TransactionRepository
from finsight.ingestion.csv_loader import load_transactions_from_csv

router = APIRouter(prefix="/api/v1/data", tags=["Data Quality"])


class DataQualityReportResponse(BaseModel):
    account_id: str
    total_transactions: int
    missing_values_pct: float
    duplicate_count: int
    invalid_amounts: int
    timestamp_gaps_days: float
    balance_reconciliation_status: str
    category_distribution: Dict[str, int]
    currency_consistency_pct: float
    data_label: str = "PRODUCTION_OR_SYNTHETIC"


class ValidateCsvResponse(BaseModel):
    valid_rows: int
    invalid_rows: int
    errors: List[Dict[str, Any]]
    schema_issues: List[Dict[str, Any]]
    sample_mapping: Dict[str, Any]


class SyntheticProfileItem(BaseModel):
    account_id: str
    profile_type: str
    transaction_count: int
    date_range: Dict[str, str]
    balance_stats: Dict[str, float]
    data_label: str = "SYNTHETIC"


@router.get("/quality-report/{account_id}", response_model=DataQualityReportResponse)
def get_data_quality_report(
    account_id: str,
    user_id: str = Depends(verify_account_ownership),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve comprehensive data quality auditing metrics for an account."""
    acc_repo = AccountRepository(db)
    acc = acc_repo.get(account_id)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found.",
        )

    tx_repo = TransactionRepository(db)
    txs = tx_repo.list_by_account(account_id)

    total_tx = len(txs)
    if total_tx == 0:
        return DataQualityReportResponse(
            account_id=account_id,
            total_transactions=0,
            missing_values_pct=0.0,
            duplicate_count=0,
            invalid_amounts=0,
            timestamp_gaps_days=0.0,
            balance_reconciliation_status="NO_DATA",
            category_distribution={},
            currency_consistency_pct=100.0,
        )

    sorted_txs = sorted(txs, key=lambda x: x.timestamp)

    # 1. Missing values percentage across optional fields (description, counterparty, balance_after)
    null_fields = sum(
        (1 if not t.description else 0)
        + (1 if not t.counterparty else 0)
        + (1 if t.balance_after is None else 0)
        for t in sorted_txs
    )
    total_checkable = total_tx * 3
    missing_pct = round((null_fields / total_checkable) * 100.0, 2)

    # 2. Duplicate detection
    seen_ids = set()
    dup_count = 0
    for t in sorted_txs:
        if t.transaction_id in seen_ids:
            dup_count += 1
        seen_ids.add(t.transaction_id)

    # 3. Invalid amounts
    invalid_amt_count = sum(1 for t in sorted_txs if t.amount <= 0)

    # 4. Max timestamp gap in days
    max_gap = 0.0
    for i in range(1, len(sorted_txs)):
        gap = (sorted_txs[i].timestamp - sorted_txs[i - 1].timestamp).total_seconds() / 86400.0
        if gap > max_gap:
            max_gap = gap

    # 5. Balance reconciliation check
    net_flow = sum(
        t.amount if t.transaction_type in ("INCOME", "REFUND", "REVERSAL") else -t.amount
        for t in sorted_txs
        if not t.is_internal_transfer
    )
    first_bal = sorted_txs[0].balance_after
    last_bal = sorted_txs[-1].balance_after
    if first_bal is not None and last_bal is not None:
        expected_last = first_bal + (net_flow - (sorted_txs[0].amount if sorted_txs[0].transaction_type == "INCOME" else -sorted_txs[0].amount))
        recon_status = "RECONCILED" if abs(expected_last - last_bal) <= 1.0 else "DISCREPANCY_DETECTED"
    else:
        recon_status = "RECONCILED"

    # 6. Category distribution
    cat_dist = Counter(t.category for t in sorted_txs)

    # 7. Currency consistency
    matching_curr = sum(1 for t in sorted_txs if t.currency == acc.currency)
    curr_consistency = round((matching_curr / total_tx) * 100.0, 2)

    return DataQualityReportResponse(
        account_id=account_id,
        total_transactions=total_tx,
        missing_values_pct=missing_pct,
        duplicate_count=dup_count,
        invalid_amounts=invalid_amt_count,
        timestamp_gaps_days=round(max_gap, 1),
        balance_reconciliation_status=recon_status,
        category_distribution=dict(cat_dist),
        currency_consistency_pct=curr_consistency,
        data_label="SYNTHETIC_SIMULATION" if "ACC_" in account_id else "PRODUCTION",
    )


@router.post("/validate-csv", response_model=ValidateCsvResponse)
async def validate_csv_dry_run(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    _rate: None = Depends(enforce_rate_limit),
):
    """Validate CSV structure, types, and financial reconciliation in dry-run mode without persisting."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a valid CSV file.",
        )

    content = await file.read()
    buffer = io.BytesIO(content)

    try:
        df_preview = pd.read_csv(io.BytesIO(content))
        sample_cols = list(df_preview.columns)
        first_row = df_preview.iloc[0].to_dict() if len(df_preview) > 0 else {}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read CSV content: {e}",
        )

    txs, report = load_transactions_from_csv(buffer)

    errors = [
        issue.model_dump()
        for issue in report.issues
        if issue.level in ("ERROR", "CRITICAL")
    ]
    schema_issues = [issue.model_dump() for issue in report.issues]

    sample_mapping = {
        "columns_detected": sample_cols,
        "sample_record": {str(k): str(v) for k, v in first_row.items()},
        "detected_account_id": report.account_id,
        "detected_currency": report.currency,
        "is_reconciled": report.reconciled,
    }

    return ValidateCsvResponse(
        valid_rows=report.valid_records,
        invalid_rows=report.rejected_records + report.duplicate_records,
        errors=errors,
        schema_issues=schema_issues,
        sample_mapping=sample_mapping,
    )


@router.get("/synthetic-profiles", response_model=List[SyntheticProfileItem])
def list_synthetic_profiles(
    user_id: str = Depends(get_current_user),
    _rate: None = Depends(enforce_rate_limit),
):
    """List benchmark synthetic profiles with transaction volumes, dates, and balance statistics."""
    csv_file = PROJECT_ROOT / "data" / "synthetic" / "transactions.csv"
    if not csv_file.exists():
        return []

    try:
        df = pd.read_csv(csv_file)
    except Exception:
        return []

    profile_type_map = {
        "ACC_001_STABLE": "Predictable Salary & Fixed Recurring Obligations",
        "ACC_002_IRREGULAR": "Freelance / Variable Income with High Discretionary Variance",
        "ACC_003_SPIKE": "Stable Salary with Episodic Large Spending Spikes",
        "ACC_004_DELAYED": "Predictable Income Subject to Delayed Payroll Cycles",
        "ACC_005_SME": "Small Business Account (Supplier Invoices & Payroll)",
        "ACC_006_COLD_START": "Cold-Start Account (< 10 Days History)",
        "ACC_007_EDGE_CASES": "Complex Edge Cases (Transfers, Refunds, Reversals)",
    }

    results: List[SyntheticProfileItem] = []
    for acc_id, grp in df.groupby("account_id"):
        acc_str = str(acc_id)
        ptype = profile_type_map.get(acc_str, "Synthetic Multi-Scenario Benchmark")

        b_min = float(grp["balance_after"].min()) if "balance_after" in grp and pd.notna(grp["balance_after"].min()) else 0.0
        b_max = float(grp["balance_after"].max()) if "balance_after" in grp and pd.notna(grp["balance_after"].max()) else 0.0
        b_latest = float(grp["balance_after"].iloc[-1]) if "balance_after" in grp and pd.notna(grp["balance_after"].iloc[-1]) else 0.0

        inc_total = float(grp[grp["transaction_type"] == "INCOME"]["amount"].sum())
        exp_total = float(grp[grp["transaction_type"] == "EXPENSE"]["amount"].sum())

        results.append(
            SyntheticProfileItem(
                account_id=acc_str,
                profile_type=ptype,
                transaction_count=len(grp),
                date_range={
                    "start": str(grp["timestamp"].min()),
                    "end": str(grp["timestamp"].max()),
                },
                balance_stats={
                    "min_balance": round(b_min, 2),
                    "max_balance": round(b_max, 2),
                    "latest_balance": round(b_latest, 2),
                    "total_inflows": round(inc_total, 2),
                    "total_outflows": round(exp_total, 2),
                },
                data_label="SYNTHETIC",
            )
        )

    return results
