"""Financial Analyst agent component translating verified model evidence."""

from typing import Dict, List, Optional
from finsight.agentic_core.schemas import AnalystOutput
from finsight.forecasting.deterministic_cashflow import CashflowForecastResult
from finsight.ml_core.predict import RiskAssessmentResult


class FinancialAnalyst:
    """Produces objective financial analysis without hallucinating numbers."""

    def analyze(
        self,
        risk: RiskAssessmentResult,
        forecast: CashflowForecastResult,
        features: Dict[str, float],
    ) -> AnalystOutput:
        """Translate model results and cash-flow forecast into structured analyst findings."""
        prob = risk.calibrated_probability
        thresh = risk.decision_threshold
        bal = features.get("verified_available_balance", 0.0)

        # 7-day projected minimum balance
        h7 = forecast.horizons.get(7, forecast.horizons.get(1))
        min_bal_7d = h7.minimum_projected_balance if h7 else bal

        # Extract drivers from SHAP or features
        drivers = []
        mitigators = []
        if risk.explanation:
            for d in risk.explanation.top_risk_drivers[:3]:
                drivers.append(f"{d.human_description} ({d.feature_name}={d.feature_value:.2f})")
            for m in risk.explanation.top_risk_mitigators[:3]:
                mitigators.append(f"{m.human_description} ({m.feature_name}={m.feature_value:.2f})")

        # Uncertainty level
        if features.get("is_cold_start", 0.0) == 1.0 or features.get("data_completeness_score", 1.0) < 0.5:
            uncertainty = "HIGH"
        elif 0.35 <= prob <= 0.65:
            uncertainty = "MODERATE"
        else:
            uncertainty = "LOW"

        # Headline
        if prob >= thresh:
            headline = f"Potential Liquidity Shortfall Warning (Probability {prob:.1%})"
        else:
            headline = f"Stable Liquidity Position (Probability {prob:.1%})"

        notes = []
        if forecast.is_cold_start:
            notes.append("Account has less than 14 days of history. Cold-start priors applied.")
        if features.get("data_staleness_days", 0.0) > 3.0:
            notes.append(f"Transaction data is {features.get('data_staleness_days', 0.0):.1f} days old.")

        return AnalystOutput(
            summary_headline=headline,
            verified_balance=round(bal, 2),
            projected_minimum_balance=round(min_bal_7d, 2),
            shortfall_probability=round(prob, 4),
            decision_threshold=round(thresh, 4),
            top_risk_drivers=drivers,
            top_mitigators=mitigators,
            uncertainty_level=uncertainty,
            data_quality_notes=notes,
        )
