"""Unit tests for deterministic PolicyEngine, action constraints, and intervention ranking."""

from datetime import datetime
from zoneinfo import ZoneInfo
import pytest

from finsight.decision.action_constraints import (
    FORBIDDEN_ESSENTIAL_CATEGORIES,
    validate_action_constraints,
)
from finsight.decision.intervention_catalog import (
    InterventionProposal,
    InterventionType,
)
from finsight.decision.policy_engine import PolicyEngine
from finsight.forecasting.deterministic_cashflow import (
    CashflowForecastResult,
    HorizonForecast,
)
from finsight.ml_core.predict import RiskAssessmentResult


@pytest.fixture
def dhaka_tz():
    return ZoneInfo("Asia/Dhaka")


@pytest.fixture
def mock_forecast():
    return CashflowForecastResult(
        account_id="ACC_TEST",
        prediction_timestamp=datetime(2024, 2, 1),
        current_balance=10000.0,
        horizons={
            7: HorizonForecast(
                horizon_days=7,
                projected_balance=400.0,
                expected_incoming=0.0,
                expected_outgoing=9600.0,
                known_obligations=5000.0,
                discretionary_modeled=4600.0,
                is_shortfall=True,
                minimum_projected_balance=400.0,
            )
        },
    )


def test_essential_bills_cannot_be_cancelled_or_paused():
    proposal = InterventionProposal(
        intervention_id="INT_ERR01",
        action_type=InterventionType.BUDGET_PROPOSAL,
        account_id="ACC_001",
        target_date=datetime(2024, 2, 1),
        predicted_probability=0.85,
        expected_cost_benefit=1.5,
        title="Cancel Rent",
        description="Attempt to cancel rent to fix cashflow",
        evidence_summary=[],
        proposed_changes={
            "category": "rent",
            "description": "Monthly rent payment",
            "cancel": True,  # Illegal!
            "pause": False,
        },
        mandatory_human_approval=True,
        is_reversible=True,
        requires_authorization=True,
        idempotency_key="key1",
    )

    is_valid, violations = validate_action_constraints(proposal)
    assert not is_valid
    assert any("rent" in v.lower() for v in violations)


def test_money_movement_operations_prohibited():
    proposal = InterventionProposal(
        intervention_id="INT_ERR02",
        action_type=InterventionType.CASHFLOW_SCENARIO,
        account_id="ACC_001",
        target_date=datetime(2024, 2, 1),
        predicted_probability=0.85,
        expected_cost_benefit=1.5,
        title="Wire Money",
        description="Attempt to initiate live wire transfer",
        evidence_summary=[],
        proposed_changes={"operation": "wire_transfer_funds"},  # Prohibited!
        mandatory_human_approval=False,
        is_reversible=False,
        requires_authorization=False,
        idempotency_key="key2",
    )

    is_valid, violations = validate_action_constraints(proposal)
    assert not is_valid
    assert any("live financial movement" in v.lower() for v in violations)


def test_policy_engine_low_risk_advisory_only(mock_forecast):
    engine = PolicyEngine(c_fn=5.0, c_fp=1.0)
    risk = RiskAssessmentResult(
        account_id="ACC_001",
        prediction_timestamp="2024-02-01T00:00:00",
        raw_probability=0.08,
        calibrated_probability=0.08,
        decision_threshold=0.1667,
        is_shortfall_predicted=False,
        risk_level="LOW",
        model_name="random_forest",
        model_version="1.0.0",
        expected_cost_of_action=0.92,
        expected_cost_of_inaction=0.40,
    )
    features = {
        "verified_available_balance": 25000.0,
        "is_cold_start": 0.0,
        "discretionary_spend_ratio_30d": 0.20,
        "known_recurring_bills_next_7d": 0.0,
    }

    proposals = engine.select_interventions(
        risk=risk,
        forecast=mock_forecast,
        account_id="ACC_001",
        features=features,
    )

    # For low risk (< 0.15), only INFORM is eligible
    action_types = [p.action_type for p in proposals]
    assert InterventionType.INFORM in action_types
    assert InterventionType.ALERT not in action_types
    assert InterventionType.HUMAN_REVIEW not in action_types


def test_policy_engine_high_risk_escalation(mock_forecast):
    engine = PolicyEngine(c_fn=5.0, c_fp=1.0)
    risk = RiskAssessmentResult(
        account_id="ACC_HIGH",
        prediction_timestamp="2024-02-01T00:00:00",
        raw_probability=0.82,
        calibrated_probability=0.82,
        decision_threshold=0.1667,
        is_shortfall_predicted=True,
        risk_level="CRITICAL",
        model_name="random_forest",
        model_version="1.0.0",
        expected_cost_of_action=0.18,
        expected_cost_of_inaction=4.10,
    )
    features = {
        "verified_available_balance": 400.0,
        "is_cold_start": 0.0,
        "discretionary_spend_ratio_30d": 0.40,
        "known_recurring_bills_next_7d": 5000.0,
    }

    proposals = engine.select_interventions(
        risk=risk,
        forecast=mock_forecast,
        account_id="ACC_HIGH",
        features=features,
    )

    action_types = [p.action_type for p in proposals]
    # Under critical risk (0.82) with high discretionary spend and upcoming bills:
    assert InterventionType.ALERT in action_types
    assert InterventionType.BUDGET_PROPOSAL in action_types
    assert InterventionType.BILL_REVIEW in action_types
    assert InterventionType.HUMAN_REVIEW in action_types

    # Ensure proposals are ranked descending by expected cost benefit
    benefits = [p.expected_cost_benefit for p in proposals]
    assert benefits == sorted(benefits, reverse=True)

