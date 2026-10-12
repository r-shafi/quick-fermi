"""Evaluation tests verifying zero lookahead feature leakage."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pytest

from finsight.features.feature_pipeline import FEATURE_COLUMNS, compute_point_in_time_features
from finsight.ingestion.schema import TransactionCategory, TransactionType, ValidatedTransaction


def test_zero_lookahead_information_leakage():
    tz = ZoneInfo("Asia/Dhaka")
    snapshot_dt = datetime(2024, 2, 1, 12, 0, tzinfo=tz)

    past_txs = [
        ValidatedTransaction(
            transaction_id="TX_PAST_01",
            account_id="ACC_LEAK_01",
            timestamp=snapshot_dt - timedelta(days=10),
            amount=50000.0,
            currency="BDT",
            transaction_type=TransactionType.INCOME,
            category=TransactionCategory.SALARY,
            is_recurring=True,
            balance_after=50000.0,
        ),
        ValidatedTransaction(
            transaction_id="TX_PAST_02",
            account_id="ACC_LEAK_01",
            timestamp=snapshot_dt - timedelta(days=5),
            amount=15000.0,
            currency="BDT",
            transaction_type=TransactionType.EXPENSE,
            category=TransactionCategory.RENT,
            is_essential=True,
            balance_after=35000.0,
        ),
    ]

    # Baseline features at snapshot_dt
    features_before = compute_point_in_time_features(past_txs, snapshot_dt)

    # Now simulate future transactions occurring AFTER snapshot_dt
    future_txs = [
        ValidatedTransaction(
            transaction_id="TX_FUT_01",
            account_id="ACC_LEAK_01",
            timestamp=snapshot_dt + timedelta(days=1),
            amount=30000.0,
            currency="BDT",
            transaction_type=TransactionType.EXPENSE,
            category=TransactionCategory.SHOPPING,
            balance_after=5000.0,
        ),
        ValidatedTransaction(
            transaction_id="TX_FUT_02",
            account_id="ACC_LEAK_01",
            timestamp=snapshot_dt + timedelta(days=3),
            amount=100000.0,
            currency="BDT",
            transaction_type=TransactionType.INCOME,
            category=TransactionCategory.INVOICE_RECEIPT,
            balance_after=105000.0,
        ),
    ]

    history_with_future = past_txs + future_txs

    # Compute features again at the same snapshot_dt with future transactions present in the list
    features_after = compute_point_in_time_features(history_with_future, snapshot_dt)

    # MUST be bit-for-bit identical for all features
    for col in FEATURE_COLUMNS:
        assert features_before[col] == pytest.approx(
            features_after[col], abs=1e-9
        ), f"Feature '{col}' leaked future data! Before: {features_before[col]}, After: {features_after[col]}"
