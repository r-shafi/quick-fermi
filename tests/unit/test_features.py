"""Unit tests for point-in-time financial feature engineering."""

from datetime import datetime, timedelta
import pytest
from zoneinfo import ZoneInfo

from finsight.features.feature_pipeline import FEATURE_COLUMNS, compute_point_in_time_features
from finsight.features.liquidity_features import extract_liquidity_features
from finsight.features.spending_features import extract_spending_features
from finsight.ingestion.reconciliation import flag_internal_transfers
from finsight.ingestion.schema import TransactionCategory, TransactionType, ValidatedTransaction


@pytest.fixture
def sample_transactions():
    tz = ZoneInfo("Asia/Dhaka")
    base_dt = datetime(2024, 1, 15, 12, 0, tzinfo=tz)

    txs = [
        ValidatedTransaction(
            transaction_id="TX001",
            account_id="ACC_TEST",
            timestamp=base_dt - timedelta(days=20),
            amount=50000.0,
            currency="BDT",
            transaction_type=TransactionType.INCOME,
            category=TransactionCategory.SALARY,
            is_recurring=True,
            balance_after=50000.0,
        ),
        ValidatedTransaction(
            transaction_id="TX002",
            account_id="ACC_TEST",
            timestamp=base_dt - timedelta(days=15),
            amount=15000.0,
            currency="BDT",
            transaction_type=TransactionType.EXPENSE,
            category=TransactionCategory.RENT,
            is_essential=True,
            is_recurring=True,
            balance_after=35000.0,
        ),
        ValidatedTransaction(
            transaction_id="TX003",
            account_id="ACC_TEST",
            timestamp=base_dt - timedelta(days=10),
            amount=10000.0,
            currency="BDT",
            transaction_type=TransactionType.TRANSFER,
            category=TransactionCategory.INTERNAL_TRANSFER,
            description="Self-transfer to savings",
            is_internal_transfer=True,
            balance_after=35000.0,
        ),
        ValidatedTransaction(
            transaction_id="TX004",
            account_id="ACC_TEST",
            timestamp=base_dt - timedelta(days=2),
            amount=2000.0,
            currency="BDT",
            transaction_type=TransactionType.EXPENSE,
            category=TransactionCategory.DINING,
            is_discretionary=True,
            balance_after=33000.0,
        ),
    ]
    return txs, base_dt


def test_internal_transfers_not_counted_as_spending(sample_transactions):
    txs, snapshot_dt = sample_transactions
    # Flag internal transfers
    flagged = flag_internal_transfers(txs)
    spend_feats = extract_spending_features(flagged, snapshot_dt)

    # Total expense should only be Rent (15000) + Dining (2000) = 17000 (transfer excluded)
    assert spend_feats["spend_sum_30d"] == 17000.0
    assert spend_feats["spend_freq_30d"] == 2.0


def test_zero_division_safety_when_no_expenses():
    tz = ZoneInfo("Asia/Dhaka")
    snapshot_dt = datetime(2024, 1, 15, tzinfo=tz)
    # Empty history
    spend_feats = extract_spending_features([], snapshot_dt)
    assert spend_feats["spending_acceleration_7_vs_30"] == 0.0
    assert spend_feats["rolling_spend_volatility_30d"] == 0.0
    assert spend_feats["essential_spend_ratio_30d"] == 0.0


def test_cold_start_uncertainty_indicator():
    tz = ZoneInfo("Asia/Dhaka")
    snapshot_dt = datetime(2024, 1, 15, tzinfo=tz)

    # 3 days of history only
    txs = [
        ValidatedTransaction(
            transaction_id="TX_NEW",
            account_id="ACC_NEW",
            timestamp=snapshot_dt - timedelta(days=3),
            amount=5000.0,
            currency="BDT",
            transaction_type=TransactionType.INCOME,
            category=TransactionCategory.SALARY,
            balance_after=5000.0,
        )
    ]

    features = extract_liquidity_features(txs, snapshot_dt)
    assert features["is_cold_start"] == 1.0
    assert features["history_days"] == 3.0
    assert features["data_completeness_score"] < 1.0


def test_feature_pipeline_schema_completeness(sample_transactions):
    txs, snapshot_dt = sample_transactions
    features = compute_point_in_time_features(txs, snapshot_dt)

    # All columns must exist and be non-null float
    for col in FEATURE_COLUMNS:
        assert col in features
        assert isinstance(features[col], float)
