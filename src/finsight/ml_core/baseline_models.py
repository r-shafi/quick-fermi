"""Baseline financial risk models."""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


class RuleBasedBaseline:
    """Deterministic rule-based liquidity runway baseline.
    
    Predicts shortfall if available balance is below safety buffer (500 BDT)
    or if estimated days of solvency is less than runway horizon (7 days).
    """

    def __init__(self, safety_buffer: float = 500.0, runway_days_threshold: float = 7.0):
        self.safety_buffer = safety_buffer
        self.runway_days_threshold = runway_days_threshold

    def fit(self, X: pd.DataFrame, y: pd.Series):
        # Rule-based model requires no training
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return deterministic pseudo-probability [P(0), P(1)]."""
        probs = []
        for _, row in X.iterrows():
            bal = float(row.get("verified_available_balance", 0.0))
            solvency = float(row.get("days_of_solvency", 999.0))
            bills_7d = float(row.get("known_recurring_bills_next_7d", 0.0))

            # Severe risk: already below buffer or bills exceed balance
            if bal < self.safety_buffer or bills_7d > bal:
                p1 = 0.95
            elif solvency < self.runway_days_threshold:
                p1 = 0.75
            elif solvency < self.runway_days_threshold * 2:
                p1 = 0.40
            else:
                p1 = 0.05

            probs.append([1.0 - p1, p1])
        return np.array(probs)

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= threshold).astype(int)


class LogisticRegressionBaseline:
    """Standard L2-regularized logistic regression with balanced class weights."""

    def __init__(self, C: float = 0.1, random_state: int = 42):
        self.scaler = StandardScaler()
        self.model = LogisticRegression(
            C=C,
            class_weight="balanced",
            max_iter=1000,
            random_state=random_state,
        )

    def fit(self, X: pd.DataFrame, y: pd.Series):
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= threshold).astype(int)
