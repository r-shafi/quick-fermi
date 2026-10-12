"""Evaluation tests for strict temporal splitting and time-ordered holdout sets."""

from pathlib import Path
import pandas as pd
import pytest

from finsight.ml_core.train import DATA_DIR, build_training_dataset


def test_temporal_split_strictly_time_ordered():
    tx_csv = DATA_DIR / "transactions.csv"
    gt_csv = DATA_DIR / "ground_truth.csv"

    assert tx_csv.exists(), f"Transactions file not found at {tx_csv}"
    assert gt_csv.exists(), f"Ground truth file not found at {gt_csv}"

    df = build_training_dataset(
        tx_csv=tx_csv,
        gt_csv=gt_csv,
        horizon_days=7,
        snapshot_interval_days=5,
    )

    assert not df.empty
    assert "snapshot_date" in df.columns
    assert "target" in df.columns

    # Check temporal split (60% Train, 20% Val, 20% Test by unique date)
    unique_dates = sorted(df["snapshot_date"].unique())
    n_dates = len(unique_dates)
    train_end_idx = int(n_dates * 0.60)
    val_end_idx = int(n_dates * 0.80)

    train_dates = unique_dates[:train_end_idx]
    val_dates = unique_dates[train_end_idx:val_end_idx]
    test_dates = unique_dates[val_end_idx:]

    train_df = df[df["snapshot_date"].isin(train_dates)]
    val_df = df[df["snapshot_date"].isin(val_dates)]
    test_df = df[df["snapshot_date"].isin(test_dates)]

    # Assert non-empty folds
    assert len(train_df) > 0
    assert len(val_df) > 0
    assert len(test_df) > 0

    max_train_date = max(train_dates)
    min_val_date = min(val_dates)
    max_val_date = max(val_dates)
    min_test_date = min(test_dates)

    # Invariants: Strict temporal ordering and zero overlap
    assert max_train_date < min_val_date, f"Overlap between train ({max_train_date}) and val ({min_val_date})"
    assert max_val_date < min_test_date, f"Overlap between val ({max_val_date}) and test ({min_test_date})"

    # Disjoint sets of dates
    assert set(train_dates).isdisjoint(set(val_dates))
    assert set(val_dates).isdisjoint(set(test_dates))
    assert set(train_dates).isdisjoint(set(test_dates))
