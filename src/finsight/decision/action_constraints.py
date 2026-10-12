"""Hard safety constraints governing financial interventions."""

from typing import List, Tuple
from finsight.decision.intervention_catalog import InterventionProposal, InterventionType

FORBIDDEN_ESSENTIAL_CATEGORIES = {
    "rent",
    "mortgage",
    "utilities",
    "electricity",
    "water",
    "gas",
    "debt_repayment",
    "loan",
    "insurance",
    "healthcare",
    "medical",
    "payroll",
    "tax",
}


class ConstraintViolationError(Exception):
    """Raised when an intervention breaches hard financial safety rules."""
    pass


def validate_action_constraints(proposal: InterventionProposal) -> Tuple[bool, List[str]]:
    """Verify that an action proposal strictly adheres to non-negotiable safety guardrails.
    
    Returns (is_valid, violation_reasons).
    """
    violations = []

    # 1. Never cancel or pause essential recurring payments
    if proposal.action_type in (InterventionType.BUDGET_PROPOSAL, InterventionType.BILL_REVIEW):
        target_category = str(proposal.proposed_changes.get("category", "")).lower()
        target_desc = str(proposal.proposed_changes.get("description", "")).lower()

        for forbidden in FORBIDDEN_ESSENTIAL_CATEGORIES:
            if forbidden in target_category or forbidden in target_desc:
                if proposal.proposed_changes.get("cancel", False) or proposal.proposed_changes.get("pause", False):
                    violations.append(
                        f"CRITICAL SAFETY VIOLATION: Cannot cancel or pause essential obligation '{forbidden}'. "
                        "Essential payments are protected by system policy."
                    )

    # 2. Never approve credit or initiate real money transfers in prototype
    proposed_op = str(proposal.proposed_changes.get("operation", "")).lower()
    if any(kw in proposed_op for kw in ["transfer", "wire", "loan_grant", "credit_increase"]):
        violations.append(
            f"FORBIDDEN OPERATION: Live financial movement '{proposed_op}' is strictly prohibited. "
            "System only operates in simulation or sandbox advisory mode."
        )

    # 3. Mandatory human approval boundary enforcement
    if proposal.action_type in (
        InterventionType.BUDGET_PROPOSAL,
        InterventionType.BILL_REVIEW,
        InterventionType.HUMAN_REVIEW,
    ):
        if not proposal.mandatory_human_approval:
            violations.append(
                f"APPROVAL INTEGRITY VIOLATION: Intervention '{proposal.action_type.value}' "
                "requires mandatory human approval and cannot be automated."
            )

    return (len(violations) == 0), violations
