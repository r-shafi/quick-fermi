"""Cost-sensitive evaluation metrics and loss formulation."""

from typing import Dict, Tuple
import numpy as np


class CostMatrix:
    """Documented asymmetric error cost matrix for financial shortfall intervention."""

    def __init__(
        self,
        c_fn: float = 5.0,
        c_fp: float = 1.0,
        c_tp: float = 0.0,
        c_tn: float = 0.0,
    ):
        self.c_fn = float(c_fn)
        self.c_fp = float(c_fp)
        self.c_tp = float(c_tp)
        self.c_tn = float(c_tn)

    def calculate_empirical_cost(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> Tuple[float, Dict[str, int]]:
        """Calculate total and confusion matrix costs under asymmetric error penalties.
        
        Cost = C_FN * FN + C_FP * FP + C_TP * TP + C_TN * TN
        """
        y_true = np.asarray(y_true).astype(int)
        y_pred = np.asarray(y_pred).astype(int)

        tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        tn = int(np.sum((y_true == 0) & (y_pred == 0)))
        fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        fn = int(np.sum((y_true == 1) & (y_pred == 0)))

        total_cost = (
            self.c_fn * fn +
            self.c_fp * fp +
            self.c_tp * tp +
            self.c_tn * tn
        )

        return float(total_cost), {"TP": tp, "TN": tn, "FP": fp, "FN": fn}

    def compute_expected_cost(
        self,
        p_shortfall: float,
        action_alert: bool,
    ) -> float:
        """Hand-verifiable analytical expected cost for continuous probability p."""
        p = float(np.clip(p_shortfall, 0.0, 1.0))
        if action_alert:
            # If we alert: (1 - p) * C_FP + p * C_TP
            return (1.0 - p) * self.c_fp + p * self.c_tp
        else:
            # If we do not alert: p * C_FN + (1 - p) * C_TN
            return p * self.c_fn + (1.0 - p) * self.c_tn

    @property
    def optimal_decision_threshold(self) -> float:
        """Analytical bayes-optimal decision threshold under cost matrix."""
        # Cost(alert) < Cost(no alert)
        # (1-p)*C_FP + p*C_TP < p*C_FN + (1-p)*C_TN
        # p * (C_FN - C_TP + C_FP - C_TN) > (C_FP - C_TN)
        denom = (self.c_fn - self.c_tp) + (self.c_fp - self.c_tn)
        if denom == 0:
            return 0.5
        return (self.c_fp - self.c_tn) / denom
