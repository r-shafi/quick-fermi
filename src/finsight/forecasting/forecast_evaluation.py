"""Evaluation metrics for cash-flow forecasting."""

from typing import Dict, List
import numpy as np


def evaluate_forecast_accuracy(
    actual_balances: List[float],
    predicted_balances: List[float],
) -> Dict[str, float]:
    """Calculate MAE, RMSE, and MAPE between predicted and actual balances."""
    act = np.array(actual_balances)
    pred = np.array(predicted_balances)

    mae = float(np.mean(np.abs(act - pred)))
    rmse = float(np.sqrt(np.mean((act - pred) ** 2)))

    # Relative MAE
    mean_actual = np.mean(np.abs(act))
    rel_mae = float(mae / (mean_actual + 1e-4))

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "relative_mae": round(rel_mae, 4),
    }


def evaluate_interval_coverage(
    actual_balances: List[float],
    lower_bounds: List[float],
    upper_bounds: List[float],
) -> Dict[str, float]:
    """Calculate empirical coverage and average width of prediction intervals."""
    act = np.array(actual_balances)
    low = np.array(lower_bounds)
    high = np.array(upper_bounds)

    covered = (act >= low) & (act <= high)
    coverage_rate = float(np.mean(covered))
    avg_width = float(np.mean(high - low))

    return {
        "empirical_coverage": round(coverage_rate, 4),
        "nominal_coverage": 0.80,  # [p10, p90] = 80% nominal
        "average_interval_width": round(avg_width, 2),
    }
