"""Independent guardrail validation component."""

from typing import List
from finsight.agentic_core.prompts import sanitize_untrusted_input
from finsight.agentic_core.schemas import GuardrailValidationResult
from finsight.decision.action_constraints import validate_action_constraints
from finsight.decision.intervention_catalog import InterventionProposal


class AgentGuardrail:
    """Independent security and financial safety guardrail."""

    def __init__(self):
        pass

    def validate_proposal(self, proposal: InterventionProposal) -> GuardrailValidationResult:
        """Independently validate a proposed intervention against hard policy boundaries."""
        violations: List[str] = []
        audit_notes: List[str] = []

        # 1. Sanitize description and title
        sanitized_title = sanitize_untrusted_input(proposal.title)
        sanitized_desc = sanitize_untrusted_input(proposal.description)

        if sanitized_desc != proposal.description or sanitized_title != proposal.title:
            audit_notes.append("Untrusted content sanitized in proposal title/description.")

        # 2. Check hard action constraints
        is_valid, constraint_violations = validate_action_constraints(proposal)
        if not is_valid:
            violations.extend(constraint_violations)

        # 3. Check for unauthorized automatic dispatch of mandatory approval actions
        if proposal.mandatory_human_approval and proposal.status == "EXECUTED":
            violations.append(
                f"UNAUTHORIZED AUTO-EXECUTION: Intervention '{proposal.action_type.value}' "
                "cannot be executed without prior verified human approval."
            )

        is_approved = len(violations) == 0
        if is_approved:
            audit_notes.append(f"Guardrail passed for intervention {proposal.intervention_id}.")

        return GuardrailValidationResult(
            is_approved=is_approved,
            violations=violations,
            sanitized_input=True,
            audit_notes=audit_notes,
        )
