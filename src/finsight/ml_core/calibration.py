"""Probability calibration using validation holdouts."""

from typing import Dict, List, Tuple
import numpy as np
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss


class ModelCalibrator:
    """Calibrates model probability outputs strictly on validation data."""

    def __init__(self, method: str = "isotonic"):
        self.method = method.lower()
        if self.method == "isotonic":
            self.regressor = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        else:
            # Sigmoid (Platt scaling) via logistic curve
            from sklearn.linear_model import LogisticRegression
            self.regressor = LogisticRegression(C=1.0, max_iter=1000)
        self.is_fitted = False

    def fit(self, val_probs: np.ndarray, y_val: np.ndarray):
        """Fit calibrator using validation probabilities only."""
        probs = np.asarray(val_probs).ravel()
        y = np.asarray(y_val).ravel()

        if self.method == "isotonic":
            self.regressor.fit(probs, y)
        else:
            self.regressor.fit(probs.reshape(-1, 1), y)
        self.is_fitted = True
        return self

    def predict_proba(self, test_probs: np.ndarray) -> np.ndarray:
        """Calibrate raw probabilities."""
        if not self.is_fitted:
            return test_probs
        probs = np.asarray(test_probs).ravel()
        if self.method == "isotonic":
            calibrated = self.regressor.predict(probs)
        else:
            calibrated = self.regressor.predict_proba(probs.reshape(-1, 1))[:, 1]
        return np.clip(calibrated, 0.0001, 0.9999)


def evaluate_calibration(
    y_true: np.ndarray,
    y_probs: np.ndarray,
    n_bins: int = 10,
) -> Dict[str, any]:
    """Compute Brier Score, Expected Calibration Error (ECE), and calibration curve."""
    y_t = np.asarray(y_true).astype(int)
    y_p = np.asarray(y_probs).astype(float)

    brier = float(brier_score_loss(y_t, y_p))

    # Calibration curve
    fraction_pos, mean_pred = calibration_curve(y_t, y_p, n_bins=n_bins, strategy="uniform")

    # ECE computation
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total_samples = len(y_t)

    for i in range(n_bins):
        bin_mask = (y_p >= bin_edges[i]) & (y_p < bin_edges[i + 1])
        if np.sum(bin_mask) > 0:
            bin_conf = np.mean(y_p[bin_mask])
            bin_acc = np.mean(y_t[bin_mask])
            bin_weight = np.sum(bin_mask) / total_samples
            ece += bin_weight * abs(bin_conf - bin_acc)

    return {
        "brier_score": round(brier, 4),
        "expected_calibration_error": round(float(ece), 4),
        "fraction_positives": [round(float(x), 4) for x in fraction_pos],
        "mean_predicted_probabilities": [round(float(x), 4) for x in mean_pred],
    }
