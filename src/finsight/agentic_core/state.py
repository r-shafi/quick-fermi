"""Agent workflow state definitions."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from finsight.agentic_core.schemas import (
    AnalystOutput,
    GuardrailValidationResult,
    StrategyPlannerOutput,
)
from finsight.decision.intervention_catalog import InterventionProposal
from finsight.forecasting.deterministic_cashflow import CashflowForecastResult
from finsight.ingestion.schema import DataQualityReport, ValidatedTransaction
from finsight.ml_core.predict import RiskAssessmentResult


class AgentWorkflowState(BaseModel):
    account_id: str
    prediction_timestamp: str
    status: str = "INITIALIZED"  # INITIALIZED, INGESTED, COMPUTED, EVALUATED, COMPLETED, FAILED
    validated_transactions: List[ValidatedTransaction] = Field(default_factory=list)
    data_quality_report: Optional[DataQualityReport] = None
    features: Dict[str, float] = Field(default_factory=dict)
    forecast: Optional[CashflowForecastResult] = None
    risk_assessment: Optional[RiskAssessmentResult] = None
    analyst_output: Optional[AnalystOutput] = None
    planner_output: Optional[StrategyPlannerOutput] = None
    guardrail_result: Optional[GuardrailValidationResult] = None
    audit_trail: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
