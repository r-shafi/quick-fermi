"""Inference service for risk prediction and SHAP explanation generation."""

from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from pydantic import BaseModel, Field

from finsight.features.feature_pipeline import FEATURE_COLUMNS
from finsight.ml_core.explainability import PredictionExplanation
from finsight.ml_core.model_registry import ARTIFACTS_DIR, RegisteredModelPackage


class RiskAssessmentResult(BaseModel):
    account_id: str
    prediction_timestamp: str
    model_version: str
    model_name: str
    raw_probability: float
    calibrated_probability: float
    decision_threshold: float
    is_shortfall_predicted: bool
    risk_level: str  # "LOW", "MODERATE", "HIGH", "CRITICAL"
    expected_cost_of_action: float
    expected_cost_of_inaction: float
    explanation: Optional[PredictionExplanation] = None
    data_quality_warnings: List[str] = Field(default_factory=list)


class RiskPredictor:
    """Predictor loaded with registered model package."""

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir
        self.package: Optional[RegisteredModelPackage] = None
        self._load_model()

    def _load_model(self):
        if self.model_dir and self.model_dir.exists():
            self.package = RegisteredModelPackage.load(self.model_dir)
            return

        # Find latest artifact in ARTIFACTS_DIR
        subdirs = [d for d in ARTIFACTS_DIR.iterdir() if d.is_dir() and (d / "metadata.json").exists()]
        if subdirs:
            # Load the first available registered model
            self.package = RegisteredModelPackage.load(subdirs[0])

    def predict_risk(
        self,
        features_dict: Dict[str, float],
        account_id: str,
        timestamp_str: str,
        c_fn: float = 5.0,
        c_fp: float = 1.0,
        warnings: Optional[List[str]] = None,
    ) -> RiskAssessmentResult:
        """Execute risk inference and explanation."""
        df_row = pd.DataFrame([features_dict])

        if self.package is None:
            # Deterministic heuristic fallback if model not trained yet
            bal = float(features_dict.get("verified_available_balance", 0.0))
            bills = float(features_dict.get("known_recurring_bills_next_7d", 0.0))
            prob = 0.85 if (bal < 500.0 or bills > bal) else 0.15
            thresh = 0.1667
            is_pred = prob >= thresh
            risk_level = "HIGH" if prob > 0.4 else "LOW"

            return RiskAssessmentResult(
                account_id=account_id,
                prediction_timestamp=timestamp_str,
                model_version="heuristic-baseline",
                model_name="rule_based",
                raw_probability=prob,
                calibrated_probability=prob,
                decision_threshold=thresh,
                is_shortfall_predicted=is_pred,
                risk_level=risk_level,
                expected_cost_of_action=round((1 - prob) * c_fp, 2),
                expected_cost_of_inaction=round(prob * c_fn, 2),
                explanation=None,
                data_quality_warnings=warnings or [],
            )

        # Use loaded model package
        cal_prob = self.package.predict_proba(df_row)
        thresh = self.package.metadata.decision_threshold
        is_pred = cal_prob >= thresh

        # Risk level categorization
        if cal_prob >= 0.70:
            risk_level = "CRITICAL"
        elif cal_prob >= 0.40:
            risk_level = "HIGH"
        elif cal_prob >= thresh:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        cost_action = (1.0 - cal_prob) * c_fp
        cost_inaction = cal_prob * c_fn

        # Generate explanation
        explanation = None
        if self.package.explainer is not None:
            try:
                explanation = self.package.explainer.explain_instance(
                    X_instance=df_row,
                    predicted_prob=cal_prob,
                    threshold=thresh,
                    warnings=warnings,
                )
            except Exception:
                explanation = None

        return RiskAssessmentResult(
            account_id=account_id,
            prediction_timestamp=timestamp_str,
            model_version=self.package.metadata.model_version,
            model_name=self.package.metadata.model_name,
            raw_probability=round(float(cal_prob), 4),
            calibrated_probability=round(float(cal_prob), 4),
            decision_threshold=round(float(thresh), 4),
            is_shortfall_predicted=is_pred,
            risk_level=risk_level,
            expected_cost_of_action=round(float(cost_action), 2),
            expected_cost_of_inaction=round(float(cost_inaction), 2),
            explanation=explanation,
            data_quality_warnings=warnings or [],
        )
