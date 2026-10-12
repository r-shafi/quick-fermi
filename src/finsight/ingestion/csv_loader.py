"""CSV transaction loader with comprehensive data quality verification."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union
import pandas as pd
from zoneinfo import ZoneInfo

from finsight.ingestion.deduplication import deduplicate_transactions
from finsight.ingestion.reconciliation import (
    flag_internal_transfers,
    reconcile_account_movements,
)
from finsight.ingestion.schema import (
    DataQualityIssue,
    DataQualityReport,
    RawTransaction,
    ValidatedTransaction,
)
from finsight.ingestion.validators import validate_raw_transaction


def load_transactions_from_csv(
    file_path_or_buffer: Union[str, Path, pd.DataFrame, Any],
    expected_currency: str = "BDT",
    opening_balance: Optional[float] = None,
    closing_balance: Optional[float] = None,
    default_tz: str = "Asia/Dhaka",
) -> Tuple[List[ValidatedTransaction], DataQualityReport]:
    """Load, validate, deduplicate, and reconcile transactions from a CSV file or buffer.
    
    Returns:
        (validated_transactions, data_quality_report)
    """
    if isinstance(file_path_or_buffer, pd.DataFrame):
        df = file_path_or_buffer.copy()
    else:
        df = pd.read_csv(file_path_or_buffer)

    total_records = len(df)
    issues: List[DataQualityIssue] = []

    # Required column check
    required_cols = {"transaction_id", "account_id", "timestamp", "amount"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        issues.append(
            DataQualityIssue(
                level="CRITICAL",
                issue_type="MISSING_COLUMNS",
                message=f"CSV is missing required columns: {sorted(list(missing_cols))}",
            )
        )
        report = DataQualityReport(
            account_id="UNKNOWN",
            total_records=total_records,
            valid_records=0,
            duplicate_records=0,
            rejected_records=total_records,
            issues=issues,
            data_completeness_score=0.0,
            currency=expected_currency,
        )
        return [], report

    account_id = str(df["account_id"].iloc[0]) if total_records > 0 else "UNKNOWN"

    raw_txs: List[RawTransaction] = []
    rejected_count = 0

    for idx, row in df.iterrows():
        try:
            raw = RawTransaction(
                transaction_id=str(row["transaction_id"]),
                account_id=str(row["account_id"]),
                timestamp=str(row["timestamp"]),
                amount=float(row["amount"]),
                currency=str(row.get("currency", expected_currency)),
                transaction_type=str(row.get("transaction_type", "EXPENSE")),
                category=str(row.get("category", "UNCERTAIN")),
                description=str(row.get("description", "")),
                counterparty=str(row.get("counterparty", "")) if pd.notna(row.get("counterparty")) else None,
                is_internal_transfer=bool(row.get("is_internal_transfer", False)),
                is_recurring=bool(row.get("is_recurring", False)),
                balance_after=float(row["balance_after"]) if pd.notna(row.get("balance_after")) else None,
            )
            raw_txs.append(raw)
        except Exception as e:
            rejected_count += 1
            issues.append(
                DataQualityIssue(
                    level="ERROR",
                    issue_type="ROW_PARSE_ERROR",
                    message=f"Failed to parse row {idx}: {e}",
                    row_index=idx,
                )
            )

    # Validate each raw transaction
    valid_txs: List[ValidatedTransaction] = []
    for idx, raw in enumerate(raw_txs):
        v_tx, issue = validate_raw_transaction(raw, expected_currency=expected_currency, row_idx=idx)
        if issue:
            issues.append(issue)
            rejected_count += 1
        elif v_tx:
            valid_txs.append(v_tx)

    # Flag internal transfers
    valid_txs = flag_internal_transfers(valid_txs)

    # Deduplicate
    unique_txs, dedup_issues = deduplicate_transactions(valid_txs)
    issues.extend(dedup_issues)
    duplicate_count = len(valid_txs) - len(unique_txs)

    # Reconcile movements
    is_reconciled, discrepancy, recon_issues = reconcile_account_movements(
        unique_txs,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
    )
    issues.extend(recon_issues)

    # Calculate data staleness and history span
    staleness_days = 0.0
    history_days = 0.0
    now_dt = datetime.now(ZoneInfo(default_tz))

    if unique_txs:
        sorted_txs = sorted(unique_txs, key=lambda x: x.timestamp)
        latest_dt = sorted_txs[-1].timestamp
        earliest_dt = sorted_txs[0].timestamp

        staleness_days = max(0.0, (now_dt - latest_dt).total_seconds() / 86400.0)
        history_days = max(0.0, (latest_dt - earliest_dt).total_seconds() / 86400.0)

    # Completeness score: penalty for rejections, missing values, duplicates
    completeness = 1.0
    if total_records > 0:
        completeness = max(0.0, (len(unique_txs) / total_records))

    report = DataQualityReport(
        account_id=account_id,
        total_records=total_records,
        valid_records=len(unique_txs),
        duplicate_records=duplicate_count,
        rejected_records=rejected_count,
        issues=issues,
        reconciled=is_reconciled,
        reconciliation_discrepancy=discrepancy,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        data_completeness_score=completeness,
        staleness_days=staleness_days,
        history_days=history_days,
        currency=expected_currency,
        has_unsupported_currency=any(i.issue_type == "UNSUPPORTED_CURRENCY_MIXING" for i in issues),
    )

    return unique_txs, report
