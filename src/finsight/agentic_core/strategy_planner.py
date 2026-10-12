"""Strategy Planner component selecting policy-compliant interventions."""

from typing import Dict, List
from finsight.agentic_core.schemas import AnalystOutput, StrategyPlannerOutput
from finsight.decision.intervention_catalog import InterventionProposal
from finsight.decision.policy_engine import PolicyEngine
from finsight.forecasting.deterministic_cashflow import CashflowForecastResult
from finsight.ml_core.predict import RiskAssessmentResult


class StrategyPlanner:
    """Selects eligible, cost-optimal financial interventions using PolicyEngine."""

    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine

    def plan(
        self,
        analyst_output: AnalystOutput,
        risk: RiskAssessmentResult,
        forecast: CashflowForecastResult,
        account_id: str,
        features: Dict[str, float],
    ) -> StrategyPlannerOutput:
        """Select eligible proposals and compile strategy rationale."""
        proposals = self.policy_engine.select_interventions(
            risk=risk,
            forecast=forecast,
            account_id=account_id,
            features=features,
        )

        requires_human = any(p.mandatory_human_approval for p in proposals)
        highest_action = proposals[0].action_type.value if proposals else None

        if not proposals:
            rationale = "No interventions warranted; account liquidity is stable or no actions pass expected cost criteria."
        else:
            rationale = (
                f"Selected {len(proposals)} eligible intervention(s) maximizing expected cost reduction. "
                f"Top priority: {highest_action} (expected benefit: {proposals[0].expected_cost_benefit:.2f})."
            )

        return StrategyPlannerOutput(
            selected_proposals=proposals,
            strategy_rationale=rationale,
            requires_human_approval=requires_human,
            highest_priority_action=highest_action,
        )
