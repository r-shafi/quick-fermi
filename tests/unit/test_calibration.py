"""Unit tests for probability calibration (Isotonic & Sigmoid) and evaluation."""

import numpy as np
import pytest

from finsight.ml_core.calibration import ModelCalibrator, evaluate_calibration


def test_model_calibrator_isotonic_bounds():
    # Uncalibrated raw probabilities with severe overconfidence
    raw_probs_val = np.array([0.1, 0.2, 0.35, 0.4, 0.65, 0.7, 0.85, 0.9])
    y_val = np.array([0, 0, 0, 1, 0, 1, 1, 1])

    calibrator = ModelCalibrator(method="isotonic")
    assert not calibrator.is_fitted

    calibrator.fit(raw_probs_val, y_val)
    assert calibrator.is_fitted

    test_probs = np.array([0.05, 0.3, 0.5, 0.8, 0.95])
    calibrated = calibrator.predict_proba(test_probs)

    assert len(calibrated) == len(test_probs)
    assert np.all(calibrated >= 0.0)
    assert np.all(calibrated <= 1.0)
    # Monotonicity check
    assert np.all(np.diff(calibrated) >= 0.0)


def test_model_calibrator_sigmoid_bounds():
    raw_probs_val = np.array([0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9])
    y_val = np.array([0, 0, 0, 0, 1, 1, 1, 1])

    calibrator = ModelCalibrator(method="sigmoid")
    calibrator.fit(raw_probs_val, y_val)

    test_probs = np.array([0.15, 0.45, 0.75])
    calibrated = calibrator.predict_proba(test_probs)

    assert len(calibrated) == 3
    assert np.all(calibrated >= 0.0)
    assert np.all(calibrated <= 1.0)


def test_evaluate_calibration_metrics():
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    # Perfectly calibrated predictions
    y_probs = np.array([0.05, 0.1, 0.15, 0.2, 0.8, 0.85, 0.9, 0.95])

    res = evaluate_calibration(y_true, y_probs, n_bins=5)
    assert "brier_score" in res
    assert "expected_calibration_error" in res
    assert res["brier_score"] < 0.05
    assert res["expected_calibration_error"] >= 0.0
