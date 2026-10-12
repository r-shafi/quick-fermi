"""Policy engine ranking interventions by expected-cost minimization and safety eligibility."""

import hashlib
from typing import Any, Dict, List, Optional, Tuple
from finsight.decision.action_constraints import validate_action_constraints
from finsight.decision.expected_cost import evaluate_action
from finsight.decision.intervention_catalog import (
    INTERVENTION_CATALOG_PARAMS,
    InterventionProposal,
    InterventionType,
)
from finsight.forecasting.deterministic_cashflow import CashflowForecastResult
from finsight.ml_core.predict import RiskAssessmentResult


class PolicyEngine:
    """Evaluates, ranks, and filters financial interventions based on cost minimization."""

    def __init__(self, c_fn: float = 5.0, c_fp: float = 1.0):
        self.c_fn = c_fn
        self.c_fp = c_fp

    def select_interventions(
        self,
        risk: RiskAssessmentResult,
        forecast: CashflowForecastResult,
        account_id: str,
        features: Dict[str, float],
    ) -> List[InterventionProposal]:
        """Rank eligible interventions by expected cost reduction."""
        prob = risk.calibrated_probability
        proposals: List[InterventionProposal] = []

        is_cold = bool(features.get("is_cold_start", 0.0))
        bills_7d = float(features.get("known_recurring_bills_next_7d", 0.0))
        discretionary_ratio = float(features.get("discretionary_spend_ratio_30d", 0.0))
        balance = float(features.get("verified_available_balance", 0.0))

        # Evaluate all catalog interventions
        for action_type, params in INTERVENTION_CATALOG_PARAMS.items():
            is_eligible = True
            eligibility_reasons = []

            # Eligibility Rules
            if action_type == InterventionType.INFORM:
                # Always eligible as passive background info
                eligibility_reasons.append("Eligible for general transparency")

            elif action_type == InterventionType.ALERT:
                if prob < 0.25:
                    is_eligible = False
                    eligibility_reasons.append("Probability below alert threshold (0.25)")
                else:
                    eligibility_reasons.append("Probability exceeds alert threshold (0.25)")

            elif action_type == InterventionType.BUDGET_PROPOSAL:
                if prob < 0.30:
                    is_eligible = False
                    eligibility_reasons.append("Probability below budget threshold (0.30)")
                elif discretionary_ratio < 0.15:
                    is_eligible = False
                    eligibility_reasons.append("Insufficient discretionary spend to propose reductions")
                else:
                    eligibility_reasons.append("Discretionary spending available for voluntary cuts")

            elif action_type == InterventionType.BILL_REVIEW:
                if prob < 0.35:
                    is_eligible = False
                    eligibility_reasons.append("Probability below bill review threshold (0.35)")
                elif bills_7d <= 0.0:
                    is_eligible = False
                    eligibility_reasons.append("No upcoming bills detected in the next 7 days")
                else:
                    eligibility_reasons.append(f"Upcoming scheduled bills total BDT {bills_7d:.2f}")

            elif action_type == InterventionType.CASHFLOW_SCENARIO:
                if prob < 0.15:
                    is_eligible = False
                    eligibility_reasons.append("Low risk does not require sandbox scenario modeling")
                else:
                    eligibility_reasons.append("Eligible for sandbox scenario exploration")

            elif action_type == InterventionType.HUMAN_REVIEW:
                if prob >= 0.70 or (is_cold and balance < 500.0):
                    eligibility_reasons.append("Critical risk or cold-start deficit triggers human review")
                else:
                    is_eligible = False
                    eligibility_reasons.append("Risk level does not warrant human escalation")

            # Evaluate expected cost and financial benefit
            eval_res = evaluate_action(
                p_shortfall=prob,
                params=params,
                c_fn=self.c_fn,
                is_eligible=is_eligible,
                eligibility_reason="; ".join(eligibility_reasons),
            )

            # Only propose if eligible and provides positive expected cost benefit (or critical human review)
            if is_eligible and (eval_res.is_cost_effective or action_type in (InterventionType.HUMAN_REVIEW, InterventionType.INFORM)):
                # Generate deterministic proposal
                idemp_raw = f"{account_id}|{action_type.value}|{risk.prediction_timestamp}|{prob:.4f}"
                idemp_key = hashlib.sha256(idemp_raw.encode("utf-8")).hexdigest()

                title, desc, changes = self._build_proposal_content(
                    action_type=action_type,
                    prob=prob,
                    features=features,
                    forecast=forecast,
                )

                evidence = [
                    f"Predicted 7-day shortfall probability: {prob:.1%}",
                    f"Decision threshold: {risk.decision_threshold:.1%}",
                    f"Current verified balance: BDT {balance:.2f}",
                    f"Expected cost reduction: {eval_res.net_cost_benefit:.2f} relative units",
                ]

                proposal = InterventionProposal(
                    intervention_id=f"INT_{idemp_key[:12].upper()}",
                    action_type=action_type,
                    account_id=account_id,
                    target_date=risk.prediction_timestamp,
                    predicted_probability=prob,
                    expected_cost_benefit=eval_res.net_cost_benefit,
                    title=title,
                    description=desc,
                    evidence_summary=evidence,
                    proposed_changes=changes,
                    mandatory_human_approval=params.mandatory_human_approval,
                    is_reversible=params.reversible,
                    requires_authorization=params.mandatory_human_approval,
                    idempotency_key=idemp_key,
                )

                # Validate constraints
                is_valid, reasons = validate_action_constraints(proposal)
                if is_valid:
                    proposals.append(proposal)

        # Sort proposals descending by expected cost benefit
        proposals.sort(key=lambda p: p.expected_cost_benefit, reverse=True)
        return proposals

    def _build_proposal_content(
        self,
        action_type: InterventionType,
        prob: float,
        features: Dict[str, float],
        forecast: CashflowForecastResult,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Construct deterministic action descriptions and structured changes."""
        bal = features.get("verified_available_balance", 0.0)

        if action_type == InterventionType.INFORM:
            return (
                "Cashflow Status Advisory",
                f"Your account balance is currently BDT {bal:.2f}. Projected 7-day minimum is BDT {forecast.horizons.get(7, forecast.horizons.get(1)).minimum_projected_balance:.2f}.",
                {"type": "informational", "mode": "display"},
            )

        elif action_type == InterventionType.ALERT:
            return (
                "Liquidity Risk Alert",
                f"High probability ({prob:.1%}) of account balance breaching minimum safety buffer within 7 days.",
                {"type": "notification", "urgency": "HIGH"},
            )

        elif action_type == InterventionType.BUDGET_PROPOSAL:
            return (
                "Suggested Discretionary Budget Adjustment",
                "Voluntarily reduce flexible entertainment and dining spending over the next 7 days by 25% to preserve cash buffer.",
                {
                    "category": "entertainment",
                    "description": "Flexible discretionary dining and entertainment",
                    "suggested_reduction_pct": 25.0,
                    "cancel": False,
                    "pause": False,
                },
            )

        elif action_type == InterventionType.BILL_REVIEW:
            return (
                "Review Upcoming Scheduled Bill",
                "An upcoming scheduled bill may cause a liquidity shortfall. Review with biller for possible payment extension.",
                {
                    "category": "bill_timing",
                    "description": "Scheduled bill timing review",
                    "request_extension_days": 5,
                    "cancel": False,
                    "pause": False,
                },
            )

        elif action_type == InterventionType.CASHFLOW_SCENARIO:
            return (
                "Interactive Sandbox Scenario Simulation",
                "Simulate cash-flow trajectory under proposed temporary spending deferrals in a zero-risk sandbox.",
                {"operation": "sandbox_simulation", "sandbox": True},
            )

        else:  # HUMAN_REVIEW
            return (
                "Escalation to Financial Specialist",
                "Account risk profile or data uncertainty requires human specialist review. No automated changes will take place.",
                {"operation": "human_escalation", "sandbox": True},
            )
