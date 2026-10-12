"""Agent workflow coordinator executing controlled multi-step state graph."""

from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from finsight.agentic_core.analyst import FinancialAnalyst
from finsight.agentic_core.guardrails import AgentGuardrail
from finsight.agentic_core.schemas import AgentExecutionResult, GuardrailValidationResult
from finsight.agentic_core.state import AgentWorkflowState
from finsight.agentic_core.strategy_planner import StrategyPlanner
from finsight.decision.intervention_catalog import InterventionProposal
from finsight.decision.policy_engine import PolicyEngine
from finsight.features.feature_pipeline import compute_point_in_time_features
from finsight.forecasting.deterministic_cashflow import forecast_deterministic_cashflow
from finsight.ingestion.schema import ValidatedTransaction
from finsight.ml_core.predict import RiskPredictor


class FinsightAgentGraph:
    """Deterministic agent state graph executing the full intervention pipeline."""

    def __init__(
        self,
        predictor: Optional[RiskPredictor] = None,
        c_fn: float = 5.0,
        c_fp: float = 1.0,
    ):
        self.predictor = predictor or RiskPredictor()
        self.policy_engine = PolicyEngine(c_fn=c_fn, c_fp=c_fp)
        self.analyst = FinancialAnalyst()
        self.planner = StrategyPlanner(self.policy_engine)
        self.guardrail = AgentGuardrail()

    def run(
        self,
        account_id: str,
        transactions: List[ValidatedTransaction],
        snapshot_dt: Optional[datetime] = None,
        current_balance: Optional[float] = None,
        is_sme: bool = False,
        tz_name: str = "Asia/Dhaka",
    ) -> AgentExecutionResult:
        """Execute complete state graph step by step."""
        tz = ZoneInfo(tz_name)
        if snapshot_dt is None:
            snapshot_dt = datetime.now(tz)
        elif snapshot_dt.tzinfo is None:
            snapshot_dt = snapshot_dt.replace(tzinfo=tz)

        ts_str = snapshot_dt.isoformat()
        audit_trail: List[str] = [f"Workflow initiated for account {account_id} at {ts_str}"]

        # 1. Point-in-time features
        features = compute_point_in_time_features(
            history=transactions,
            snapshot_dt=snapshot_dt,
            current_balance=current_balance,
            is_sme=is_sme,
        )
        audit_trail.append(f"Computed {len(features)} point-in-time features without lookahead leakage.")

        # 2. Cashflow Forecast
        balance = float(features.get("verified_available_balance", 0.0))
        forecast = forecast_deterministic_cashflow(
            history=transactions,
            current_balance=balance,
            snapshot_dt=snapshot_dt,
            account_id=account_id,
        )
        audit_trail.append("Computed deterministic cash-flow trajectory across 1, 3, 7, and 14 days.")

        # 3. Predict Shortfall Risk & SHAP
        risk = self.predictor.predict_risk(
            features_dict=features,
            account_id=account_id,
            timestamp_str=ts_str,
            c_fn=self.policy_engine.c_fn,
            c_fp=self.policy_engine.c_fp,
        )
        audit_trail.append(
            f"Risk predicted: p={risk.calibrated_probability:.1%}, threshold={risk.decision_threshold:.1%}, "
            f"risk_level={risk.risk_level}"
        )

        # 4. Analyst Synthesis
        analyst_out = self.analyst.analyze(
            risk=risk,
            forecast=forecast,
            features=features,
        )
        audit_trail.append("Analyst synthesized verified evidence and risk drivers.")

        # 5. Strategy Planning
        plan_out = self.planner.plan(
            analyst_output=analyst_out,
            risk=risk,
            forecast=forecast,
            account_id=account_id,
            features=features,
        )
        audit_trail.append(f"Strategy planner selected {len(plan_out.selected_proposals)} interventions.")

        # 6. Guardrail Check on every proposal
        validated_proposals: List[InterventionProposal] = []
        guardrail_violations: List[str] = []
        guardrail_notes: List[str] = []

        for prop in plan_out.selected_proposals:
            g_res = self.guardrail.validate_proposal(prop)
            if g_res.is_approved:
                validated_proposals.append(prop)
                guardrail_notes.extend(g_res.audit_notes)
            else:
                guardrail_violations.extend(g_res.violations)
                audit_trail.append(f"GUARDRAIL REJECTED proposal {prop.intervention_id}: {g_res.violations}")

        final_guardrail_res = GuardrailValidationResult(
            is_approved=len(guardrail_violations) == 0,
            violations=guardrail_violations,
            sanitized_input=True,
            audit_notes=guardrail_notes,
        )

        audit_trail.append("Workflow execution finished successfully.")

        return AgentExecutionResult(
            account_id=account_id,
            timestamp=ts_str,
            workflow_status="COMPLETED",
            analyst_summary=analyst_out,
            risk_assessment=risk,
            forecast=forecast,
            proposals=validated_proposals,
            guardrail_result=final_guardrail_res,
            audit_trail=audit_trail,
        )
