"""Unit tests for deterministic and probabilistic cash-flow forecasting."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pytest

from finsight.forecasting.deterministic_cashflow import (
    CashflowForecastResult,
    forecast_deterministic_cashflow,
)
from finsight.forecasting.probabilistic_forecaster import (
    ProbabilisticCashflowResult,
    forecast_probabilistic_cashflow,
)
from finsight.forecasting.forecast_evaluation import (
    evaluate_forecast_accuracy,
    evaluate_interval_coverage,
)
from finsight.ingestion.schema import (
    TransactionCategory,
    TransactionType,
    ValidatedTransaction,
)


@pytest.fixture
def dhaka_tz():
    return ZoneInfo("Asia/Dhaka")


def test_deterministic_balance_roll_forward(dhaka_tz):
    snapshot_dt = datetime(2024, 2, 1, tzinfo=dhaka_tz)
    starting_balance = 20000.0

    # Past salary and rent
    history = [
        ValidatedTransaction(
            transaction_id="TX001",
            account_id="ACC_001",
            timestamp=snapshot_dt - timedelta(days=20),
            amount=50000.0,
            currency="BDT",
            transaction_type=TransactionType.INCOME,
            category=TransactionCategory.SALARY,
            is_recurring=True,
            balance_after=50000.0,
        ),
        # Recurring utility bill on day 10
        ValidatedTransaction(
            transaction_id="TX002",
            account_id="ACC_001",
            timestamp=snapshot_dt - timedelta(days=22),
            amount=5000.0,
            currency="BDT",
            transaction_type=TransactionType.EXPENSE,
            category=TransactionCategory.UTILITIES,
            is_recurring=True,
            balance_after=45000.0,
        ),
    ]

    res = forecast_deterministic_cashflow(
        history=history,
        current_balance=starting_balance,
        snapshot_dt=snapshot_dt,
        account_id="ACC_001",
        horizons=[1, 3, 7, 14],
        safety_buffer=500.0,
    )

    assert isinstance(res, CashflowForecastResult)
    assert 7 in res.horizons
    h7 = res.horizons[7]
    assert h7.horizon_days == 7
    assert len(res.daily_balance_trajectory) == 14
    assert res.current_balance == starting_balance


def test_deterministic_shortfall_detection(dhaka_tz):
    snapshot_dt = datetime(2024, 2, 1, tzinfo=dhaka_tz)
    starting_balance = 1000.0

    # Low balance with high daily spend
    history = [
        ValidatedTransaction(
            transaction_id="TX_SPEND_1",
            account_id="ACC_LOW",
            timestamp=snapshot_dt - timedelta(days=5),
            amount=3000.0,
            currency="BDT",
            transaction_type=TransactionType.EXPENSE,
            category=TransactionCategory.GROCERIES,
            balance_after=1000.0,
        ),
        ValidatedTransaction(
            transaction_id="TX_SPEND_2",
            account_id="ACC_LOW",
            timestamp=snapshot_dt - timedelta(days=2),
            amount=3000.0,
            currency="BDT",
            transaction_type=TransactionType.EXPENSE,
            category=TransactionCategory.DINING,
            balance_after=1000.0,
        ),
    ]

    res = forecast_deterministic_cashflow(
        history=history,
        current_balance=starting_balance,
        snapshot_dt=snapshot_dt,
        account_id="ACC_LOW",
        horizons=[7],
        safety_buffer=500.0,
    )

    h7 = res.horizons[7]
    # Projected balance drops below 500 buffer
    assert h7.minimum_projected_balance < 500.0
    assert h7.is_shortfall is True


def test_probabilistic_forecast_quantiles(dhaka_tz):
    snapshot_dt = datetime(2024, 2, 1, tzinfo=dhaka_tz)

    history = [
        ValidatedTransaction(
            transaction_id="TX_P1",
            account_id="ACC_PROB",
            timestamp=snapshot_dt - timedelta(days=15),
            amount=40000.0,
            currency="BDT",
            transaction_type=TransactionType.INCOME,
            category=TransactionCategory.SALARY,
            balance_after=40000.0,
        )
    ]

    res = forecast_probabilistic_cashflow(
        history=history,
        current_balance=25000.0,
        snapshot_dt=snapshot_dt,
        account_id="ACC_PROB",
        horizons=[1, 3, 7, 14],
        safety_buffer=500.0,
        n_simulations=100,
    )

    assert isinstance(res, ProbabilisticCashflowResult)
    assert len(res.daily_intervals) == 14

    for day_interval in res.daily_intervals:
        p10 = day_interval["lower_p10"]
        p50 = day_interval["median_p50"]
        p90 = day_interval["upper_p90"]
        # Quantile ordering invariant: P10 <= P50 <= P90
        assert p10 <= p50 <= p90

    # Horizon checks
    for h, h_res in res.horizons.items():
        assert h_res.lower_bound_p10 <= h_res.projected_balance_median <= h_res.upper_bound_p90
        assert h_res.interval_width == pytest.approx(h_res.upper_bound_p90 - h_res.lower_bound_p10, abs=0.05)



def test_forecast_evaluation_metrics():
    y_true = [1000.0, 950.0, 900.0, 850.0]
    y_pred = [1010.0, 940.0, 890.0, 860.0]

    point_eval = evaluate_forecast_accuracy(y_true, y_pred)
    assert point_eval["mae"] == 10.0
    assert point_eval["rmse"] == 10.0

    p10 = [900.0, 850.0, 800.0, 750.0]
    p90 = [1100.0, 1050.0, 1000.0, 950.0]
    interval_eval = evaluate_interval_coverage(y_true, p10, p90)

    assert interval_eval["empirical_coverage"] == 1.0  # 100% of points fall inside [p10, p90]
    assert interval_eval["average_interval_width"] == 200.0

