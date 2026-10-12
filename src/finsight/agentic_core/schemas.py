"""Pydantic schemas for structured agent outputs and state transitions."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from finsight.decision.intervention_catalog import InterventionProposal
from finsight.forecasting.deterministic_cashflow import CashflowForecastResult
from finsight.ml_core.explainability import PredictionExplanation
from finsight.ml_core.predict import RiskAssessmentResult


class AnalystOutput(BaseModel):
    summary_headline: str
    verified_balance: float
    projected_minimum_balance: float
    shortfall_probability: float
    decision_threshold: float
    top_risk_drivers: List[str] = Field(default_factory=list)
    top_mitigators: List[str] = Field(default_factory=list)
    uncertainty_level: str  # "LOW", "MODERATE", "HIGH"
    data_quality_notes: List[str] = Field(default_factory=list)


class StrategyPlannerOutput(BaseModel):
    selected_proposals: List[InterventionProposal] = Field(default_factory=list)
    strategy_rationale: str
    requires_human_approval: bool
    highest_priority_action: Optional[str] = None


class GuardrailValidationResult(BaseModel):
    is_approved: bool
    violations: List[str] = Field(default_factory=list)
    sanitized_input: bool = True
    audit_notes: List[str] = Field(default_factory=list)


class AgentExecutionResult(BaseModel):
    account_id: str
    timestamp: str
    workflow_status: str  # "COMPLETED", "FALLBACK_APPLIED", "GUARDRAIL_BLOCKED"
    analyst_summary: AnalystOutput
    risk_assessment: RiskAssessmentResult
    forecast: CashflowForecastResult
    proposals: List[InterventionProposal] = Field(default_factory=list)
    guardrail_result: GuardrailValidationResult
    audit_trail: List[str] = Field(default_factory=list)
