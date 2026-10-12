"""Drift monitoring and population stability index (PSI) detection."""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd


def calculate_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    num_buckets: int = 10,
    epsilon: float = 1e-4,
) -> float:
    """Compute Population Stability Index (PSI) between baseline and production distributions.
    
    PSI < 0.1: No significant change
    0.1 <= PSI < 0.25: Moderate shift, investigation warranted
    PSI >= 0.25: Significant shift, retraining review required
    """
    exp = np.asarray(expected).ravel()
    act = np.asarray(actual).ravel()

    if len(exp) == 0 or len(act) == 0:
        return 0.0

    # Quantile bin edges from expected distribution
    percentiles = np.linspace(0, 100, num_buckets + 1)
    bin_edges = np.percentile(exp, percentiles)
    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf

    # Bucket counts
    exp_counts, _ = np.histogram(exp, bins=bin_edges)
    act_counts, _ = np.histogram(act, bins=bin_edges)

    exp_pct = exp_counts / max(1, len(exp))
    act_pct = act_counts / max(1, len(act))

    # Avoid zero division
    exp_pct = np.where(exp_pct == 0, epsilon, exp_pct)
    act_pct = np.where(act_pct == 0, epsilon, act_pct)

    psi_val = np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct))
    return float(max(0.0, psi_val))


class ModelDriftMonitor:
    """Monitors model output score distributions and key feature drift."""

    def __init__(
        self,
        baseline_scores: np.ndarray,
        baseline_features: pd.DataFrame,
        psi_threshold_warning: float = 0.10,
        psi_threshold_critical: float = 0.25,
    ):
        self.baseline_scores = baseline_scores
        self.baseline_features = baseline_features
        self.psi_threshold_warning = psi_threshold_warning
        self.psi_threshold_critical = psi_threshold_critical

    def evaluate_drift(
        self,
        current_scores: np.ndarray,
        current_features: pd.DataFrame,
    ) -> Dict[str, any]:
        """Assess drift on predictions and features.
        
        Strict policy: A drift alert generates investigation notifications and flags
        for retraining approval. It NEVER automatically deploys a new unvalidated model.
        """
        score_psi = calculate_psi(self.baseline_scores, current_scores)

        feature_psi_map = {}
        drifted_features = []

        common_cols = [c for c in self.baseline_features.columns if c in current_features.columns]
        for col in common_cols:
            psi_val = calculate_psi(
                self.baseline_features[col].dropna().values,
                current_features[col].dropna().values,
            )
            feature_psi_map[col] = round(psi_val, 4)
            if psi_val >= self.psi_threshold_warning:
                drifted_features.append(col)

        has_drift_warning = score_psi >= self.psi_threshold_warning or len(drifted_features) > 0
        is_critical = score_psi >= self.psi_threshold_critical or any(
            v >= self.psi_threshold_critical for v in feature_psi_map.values()
        )

        status = "CRITICAL_DRIFT" if is_critical else ("WARNING_DRIFT" if has_drift_warning else "HEALTHY")

        recommended_action = (
            "Initiate offline retraining with human approval review. Model replacement blocked."
            if has_drift_warning else "Continue monitoring."
        )

        return {
            "status": status,
            "score_psi": round(score_psi, 4),
            "drifted_features_count": len(drifted_features),
            "drifted_features": drifted_features,
            "feature_psi": feature_psi_map,
            "recommended_action": recommended_action,
            "auto_deployment_permitted": False,  # Safety guarantee
        }
