"""Approved Intervention Catalog and Action Metadata."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from finsight.decision.expected_cost import InterventionCostParameters


class InterventionType(str, Enum):
    INFORM = "INFORM"
    ALERT = "ALERT"
    BUDGET_PROPOSAL = "BUDGET_PROPOSAL"
    BILL_REVIEW = "BILL_REVIEW"
    CASHFLOW_SCENARIO = "CASHFLOW_SCENARIO"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class InterventionProposal(BaseModel):
    intervention_id: str
    action_type: InterventionType
    account_id: str
    target_date: Union[datetime, str]
    predicted_probability: float
    expected_cost_benefit: float
    title: str
    description: str
    evidence_summary: List[str] = Field(default_factory=list)
    proposed_changes: Dict[str, Any] = Field(default_factory=dict)
    mandatory_human_approval: bool
    is_reversible: bool
    requires_authorization: bool
    idempotency_key: str
    status: str = "PROPOSED"


# Default catalog cost configurations
INTERVENTION_CATALOG_PARAMS: Dict[InterventionType, InterventionCostParameters] = {
    InterventionType.INFORM: InterventionCostParameters(
        action_type="INFORM",
        intervention_cost=0.0,
        risk_reduction_factor=0.05,
        unnecessary_cost=0.1,
        mandatory_human_approval=False,
        reversible=True,
    ),
    InterventionType.ALERT: InterventionCostParameters(
        action_type="ALERT",
        intervention_cost=0.1,
        risk_reduction_factor=0.35,
        unnecessary_cost=1.0,
        mandatory_human_approval=False,
        reversible=True,
    ),
    InterventionType.BUDGET_PROPOSAL: InterventionCostParameters(
        action_type="BUDGET_PROPOSAL",
        intervention_cost=0.5,
        risk_reduction_factor=0.50,
        unnecessary_cost=1.5,
        mandatory_human_approval=True,
        reversible=True,
    ),
    InterventionType.BILL_REVIEW: InterventionCostParameters(
        action_type="BILL_REVIEW",
        intervention_cost=0.8,
        risk_reduction_factor=0.60,
        unnecessary_cost=2.0,
        mandatory_human_approval=True,
        reversible=True,
    ),
    InterventionType.CASHFLOW_SCENARIO: InterventionCostParameters(
        action_type="CASHFLOW_SCENARIO",
        intervention_cost=0.2,
        risk_reduction_factor=0.40,
        unnecessary_cost=0.5,
        mandatory_human_approval=False,
        reversible=True,
    ),
    InterventionType.HUMAN_REVIEW: InterventionCostParameters(
        action_type="HUMAN_REVIEW",
        intervention_cost=2.5,
        risk_reduction_factor=0.85,
        unnecessary_cost=4.0,
        mandatory_human_approval=True,
        reversible=False,
    ),
}
