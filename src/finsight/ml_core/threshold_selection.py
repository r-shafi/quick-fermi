"""Cost-sensitive threshold selection."""

from typing import Dict, List, Tuple
import numpy as np
from finsight.ml_core.cost_sensitive_loss import CostMatrix


def select_optimal_threshold(
    val_probs: np.ndarray,
    y_val: np.ndarray,
    cost_matrix: CostMatrix,
    n_thresholds: int = 100,
) -> Tuple[float, float, List[Dict[str, float]]]:
    """Find the threshold tau* on validation data that minimizes total financial cost.
    
    Returns:
        (optimal_threshold, min_cost, sensitivity_curve)
    """
    thresholds = np.linspace(0.01, 0.99, n_thresholds)
    best_threshold = cost_matrix.optimal_decision_threshold
    min_cost = float("inf")
    curve = []

    for tau in thresholds:
        y_pred = (val_probs >= tau).astype(int)
        cost, cm = cost_matrix.calculate_empirical_cost(y_val, y_pred)
        
        entry = {
            "threshold": round(float(tau), 4),
            "total_cost": round(cost, 2),
            "false_negatives": cm["FN"],
            "false_positives": cm["FP"],
            "true_positives": cm["TP"],
            "true_negatives": cm["TN"],
        }
        curve.append(entry)

        if cost < min_cost:
            min_cost = cost
            best_threshold = float(tau)

    return best_threshold, min_cost, curve
