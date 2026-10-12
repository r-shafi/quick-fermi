"""Expected-cost mathematical formulation for financial intervention selection."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class InterventionCostParameters(BaseModel):
    action_type: str
    intervention_cost: float
    risk_reduction_factor: float  # alpha in [0, 1]
    unnecessary_cost: float       # Cost if shortfall does not occur
    mandatory_human_approval: bool
    reversible: bool


class ActionEvaluation(BaseModel):
    action_type: str
    expected_cost_with_action: float
    expected_cost_without_action: float
    net_cost_benefit: float
    is_cost_effective: bool
    is_eligible: bool
    eligibility_reason: str
    parameters: InterventionCostParameters


def compute_expected_cost_for_action(
    p_shortfall: float,
    params: InterventionCostParameters,
    c_fn: float = 5.0,
) -> float:
    """Compute expected cost of applying intervention action a under shortfall probability p.
    
    Formula:
      E[Cost(a | p)] = (1 - p) * C_unnecessary + p * (1 - alpha_a) * C_FN + C_a
    """
    p = float(max(0.0, min(1.0, p_shortfall)))
    cost = (
        (1.0 - p) * params.unnecessary_cost +
        p * (1.0 - params.risk_reduction_factor) * c_fn +
        params.intervention_cost
    )
    return float(cost)


def compute_expected_cost_inaction(
    p_shortfall: float,
    c_fn: float = 5.0,
) -> float:
    """Compute expected cost of taking no intervention.
    
    Formula:
      E[Cost(none | p)] = p * C_FN
    """
    p = float(max(0.0, min(1.0, p_shortfall)))
    return float(p * c_fn)


def evaluate_action(
    p_shortfall: float,
    params: InterventionCostParameters,
    c_fn: float = 5.0,
    is_eligible: bool = True,
    eligibility_reason: str = "Eligible under policy rules",
) -> ActionEvaluation:
    """Evaluate financial expected cost and benefit for a proposed intervention."""
    cost_with = compute_expected_cost_for_action(p_shortfall, params, c_fn=c_fn)
    cost_without = compute_expected_cost_inaction(p_shortfall, c_fn=c_fn)
    net_benefit = cost_without - cost_with

    return ActionEvaluation(
        action_type=params.action_type,
        expected_cost_with_action=round(cost_with, 4),
        expected_cost_without_action=round(cost_without, 4),
        net_cost_benefit=round(net_benefit, 4),
        is_cost_effective=net_benefit > 0.0,
        is_eligible=is_eligible,
        eligibility_reason=eligibility_reason,
        parameters=params,
    )
