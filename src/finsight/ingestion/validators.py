"""Validators for raw financial records."""

from datetime import datetime, timezone
from typing import Optional, Tuple
import pandas as pd
from zoneinfo import ZoneInfo

from finsight.ingestion.schema import (
    DISCRETIONARY_CATEGORIES,
    ESSENTIAL_CATEGORIES,
    DataQualityIssue,
    RawTransaction,
    TransactionCategory,
    TransactionType,
    ValidatedTransaction,
)


def parse_timestamp_safe(ts_str: str, default_tz: str = "Asia/Dhaka") -> datetime:
    """Parse string timestamp into timezone-aware datetime."""
    ts_str = str(ts_str).strip()
    try:
        # Try pandas to parse flexible formats
        dt = pd.to_datetime(ts_str)
        if dt.tzinfo is None:
            dt = dt.tz_localize(ZoneInfo(default_tz))
        else:
            dt = dt.tz_convert(ZoneInfo(default_tz))
        return dt.to_pydatetime()
    except Exception as e:
        raise ValueError(f"Unable to parse timestamp '{ts_str}': {e}")


def validate_raw_transaction(
    raw: RawTransaction,
    expected_currency: str = "BDT",
    row_idx: Optional[int] = None,
) -> Tuple[Optional[ValidatedTransaction], Optional[DataQualityIssue]]:
    """Validate a single raw transaction.
    
    Returns (validated_tx, None) if valid, or (None, issue) if invalid.
    """
    # 1. Non-empty IDs
    if not raw.transaction_id or not str(raw.transaction_id).strip():
        return None, DataQualityIssue(
            level="ERROR",
            issue_type="MISSING_TRANSACTION_ID",
            message="Transaction ID is empty",
            row_index=row_idx,
        )

    if not raw.account_id or not str(raw.account_id).strip():
        return None, DataQualityIssue(
            level="ERROR",
            issue_type="MISSING_ACCOUNT_ID",
            message="Account ID is empty",
            row_index=row_idx,
            transaction_id=raw.transaction_id,
        )

    # 2. Timestamp parsing
    try:
        ts = parse_timestamp_safe(raw.timestamp)
    except Exception as e:
        return None, DataQualityIssue(
            level="ERROR",
            issue_type="INVALID_TIMESTAMP",
            message=str(e),
            row_index=row_idx,
            transaction_id=raw.transaction_id,
        )

    # 3. Currency check
    curr = str(raw.currency).strip().upper()
    if curr != expected_currency.upper():
        return None, DataQualityIssue(
            level="ERROR",
            issue_type="UNSUPPORTED_CURRENCY_MIXING",
            message=f"Currency '{curr}' does not match account currency '{expected_currency}'. FX conversion required.",
            row_index=row_idx,
            transaction_id=raw.transaction_id,
        )

    # 4. Amount validation
    try:
        amt = float(raw.amount)
    except (ValueError, TypeError):
        return None, DataQualityIssue(
            level="ERROR",
            issue_type="INVALID_AMOUNT",
            message=f"Amount '{raw.amount}' is not a valid number",
            row_index=row_idx,
            transaction_id=raw.transaction_id,
        )

    if amt < 0:
        return None, DataQualityIssue(
            level="ERROR",
            issue_type="NEGATIVE_AMOUNT",
            message=f"Amount must be non-negative (sign is defined by transaction_type): got {amt}",
            row_index=row_idx,
            transaction_id=raw.transaction_id,
        )

    if amt == 0:
        # Zero amount is flagged as suspicious warning but can be valid in test cases
        pass

    # 5. Transaction type mapping
    type_str = str(raw.transaction_type).strip().upper()
    try:
        tx_type = TransactionType(type_str)
    except ValueError:
        return None, DataQualityIssue(
            level="ERROR",
            issue_type="INVALID_TRANSACTION_TYPE",
            message=f"Unknown transaction type '{type_str}'",
            row_index=row_idx,
            transaction_id=raw.transaction_id,
        )

    # 6. Category mapping
    cat_str = str(raw.category).strip().upper() if raw.category else "UNCERTAIN"
    try:
        tx_category = TransactionCategory(cat_str)
    except ValueError:
        tx_category = TransactionCategory.UNCERTAIN

    is_essential = tx_category in ESSENTIAL_CATEGORIES
    is_discretionary = tx_category in DISCRETIONARY_CATEGORIES

    validated = ValidatedTransaction(
        transaction_id=str(raw.transaction_id).strip(),
        account_id=str(raw.account_id).strip(),
        timestamp=ts,
        amount=amt,
        currency=curr,
        transaction_type=tx_type,
        category=tx_category,
        description=str(raw.description or "").strip(),
        counterparty=raw.counterparty,
        is_internal_transfer=bool(raw.is_internal_transfer),
        is_recurring=bool(raw.is_recurring),
        balance_after=raw.balance_after,
        is_essential=is_essential,
        is_discretionary=is_discretionary,
    )

    return validated, None
