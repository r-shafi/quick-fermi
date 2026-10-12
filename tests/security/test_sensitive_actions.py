"""Security tests ensuring sensitive financial actions are strictly forbidden."""

import pytest

from finsight.decision.action_constraints import (
    FORBIDDEN_ESSENTIAL_CATEGORIES,
    validate_action_constraints,
)
from finsight.decision.intervention_catalog import (
    InterventionProposal,
    InterventionType,
)


@pytest.mark.parametrize("category", list(FORBIDDEN_ESSENTIAL_CATEGORIES))
def test_all_essential_categories_protected_from_cancellation(category):
    proposal = InterventionProposal(
        intervention_id="INT_FORBIDDEN_001",
        action_type=InterventionType.BUDGET_PROPOSAL,
        account_id="ACC_001_STABLE",
        target_date="2024-02-01T00:00:00",
        predicted_probability=0.9,
        expected_cost_benefit=2.0,
        title=f"Cancel {category}",
        description=f"Automated policy attempt to cancel {category}",
        evidence_summary=[],
        proposed_changes={"category": category, "cancel": True},
        mandatory_human_approval=True,
        is_reversible=True,
        requires_authorization=True,
        idempotency_key=f"idemp_cancel_{category}",
    )

    is_valid, violations = validate_action_constraints(proposal)
    assert not is_valid
    assert any("essential payment" in v.lower() or category in v.lower() for v in violations)


@pytest.mark.parametrize("category", ["rent", "utilities", "payroll", "tax", "debt_repayment"])
def test_all_essential_categories_protected_from_pause(category):
    proposal = InterventionProposal(
        intervention_id="INT_FORBIDDEN_002",
        action_type=InterventionType.BILL_REVIEW,
        account_id="ACC_001_STABLE",
        target_date="2024-02-01T00:00:00",
        predicted_probability=0.9,
        expected_cost_benefit=2.0,
        title=f"Pause {category}",
        description=f"Automated policy attempt to pause {category}",
        evidence_summary=[],
        proposed_changes={"category": category, "pause": True},
        mandatory_human_approval=True,
        is_reversible=True,
        requires_authorization=True,
        idempotency_key=f"idemp_pause_{category}",
    )

    is_valid, violations = validate_action_constraints(proposal)
    assert not is_valid


@pytest.mark.parametrize("op", ["transfer", "wire_out", "loan_grant", "credit_increase"])
def test_live_financial_movements_rejected(op):
    proposal = InterventionProposal(
        intervention_id="INT_FORBIDDEN_003",
        action_type=InterventionType.CASHFLOW_SCENARIO,
        account_id="ACC_001_STABLE",
        target_date="2024-02-01T00:00:00",
        predicted_probability=0.5,
        expected_cost_benefit=1.0,
        title=f"Execute {op}",
        description=f"Attempt to initiate {op}",
        evidence_summary=[],
        proposed_changes={"operation": op},
        mandatory_human_approval=False,
        is_reversible=False,
        requires_authorization=False,
        idempotency_key=f"idemp_op_{op}",
    )

    is_valid, violations = validate_action_constraints(proposal)
    assert not is_valid
    assert any("strictly prohibited" in v.lower() for v in violations)


def test_mandatory_human_approval_bypass_rejected():
    # Budget proposal without mandatory human approval must be rejected
    proposal = InterventionProposal(
        intervention_id="INT_FORBIDDEN_004",
        action_type=InterventionType.BUDGET_PROPOSAL,
        account_id="ACC_001_STABLE",
        target_date="2024-02-01T00:00:00",
        predicted_probability=0.6,
        expected_cost_benefit=1.0,
        title="Unattended budget modification",
        description="Try to automate budget without human signoff",
        evidence_summary=[],
        proposed_changes={"category": "entertainment", "suggested_reduction_pct": 10.0},
        mandatory_human_approval=False,  # Bypass attempt
        is_reversible=True,
        requires_authorization=False,
        idempotency_key="idemp_bypass_approval",
    )

    is_valid, violations = validate_action_constraints(proposal)
    assert not is_valid
    assert any("requires mandatory human approval" in v.lower() for v in violations)
