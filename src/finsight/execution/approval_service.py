"""Human approval workflow service managing state transitions and sandbox execution."""

import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from finsight.database.repositories import ApprovalRepository
from finsight.decision.action_constraints import validate_action_constraints
from finsight.decision.intervention_catalog import (
    InterventionProposal,
    InterventionType,
)
from finsight.execution.action_dispatcher import action_dispatcher
from finsight.execution.audit_log import AuditLogger
from finsight.execution.idempotency import idempotency_store


class ApprovalService:
    """Manages the full lifecycle of human approvals and sandbox dispatches."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.repo = ApprovalRepository(db) if db else None
        self.audit = AuditLogger(db)

    def submit_proposal(self, proposal: InterventionProposal) -> Dict[str, any]:
        """Submit an intervention proposal into the approval queue or auto-dispatch if exempt."""
        # 1. Guardrail validation
        is_valid, violations = validate_action_constraints(proposal)
        if not is_valid:
            self.audit.record(
                actor="POLICY_ENGINE",
                account_id=proposal.account_id,
                action="SUBMIT_PROPOSAL",
                status="REJECTED_BY_GUARDRAIL",
                details={"violations": violations},
            )
            raise ValueError(f"Proposal violated policy constraints: {violations}")

        # 2. Idempotency check
        if not idempotency_store.check_and_set(proposal.idempotency_key):
            # Duplicate detected
            return {
                "status": "DUPLICATE_IGNORED",
                "message": f"Proposal with key {proposal.idempotency_key} already submitted.",
            }

        approval_id = f"APP_{proposal.intervention_id}"

        # 3. If action requires human approval
        if proposal.mandatory_human_approval:
            if self.repo:
                self.repo.create(
                    approval_id=approval_id,
                    intervention_id=proposal.intervention_id,
                    account_id=proposal.account_id,
                    action_type=proposal.action_type.value,
                    title=proposal.title,
                    description=proposal.description,
                    proposed_changes=proposal.proposed_changes,
                    idempotency_key=proposal.idempotency_key,
                    status="PENDING_APPROVAL",
                )

            self.audit.record(
                actor="SYSTEM_AGENT",
                account_id=proposal.account_id,
                action="PROPOSE_INTERVENTION",
                status="PENDING_APPROVAL",
                details={
                    "approval_id": approval_id,
                    "action_type": proposal.action_type.value,
                    "title": proposal.title,
                },
            )

            return {
                "approval_id": approval_id,
                "status": "PENDING_APPROVAL",
                "message": "Intervention requires human review and is queued for approval.",
                "proposal": proposal.model_dump(),
            }

        # 4. If action does not require human approval, auto-dispatch to sandbox
        outcome = action_dispatcher.dispatch(proposal)
        idempotency_store.mark_completed(proposal.idempotency_key)

        self.audit.record(
            actor="SYSTEM_AGENT",
            account_id=proposal.account_id,
            action="AUTO_DISPATCH",
            status=outcome.status,
            details={"dispatch_id": outcome.dispatch_id, "message": outcome.message},
        )

        return {
            "approval_id": approval_id,
            "status": outcome.status,
            "message": outcome.message,
            "proposal": proposal.model_dump(),
        }

    def approve(self, approval_id: str, actor_id: str) -> Dict[str, any]:
        """User or authorized actor approves a pending intervention."""
        record = self.repo.get(approval_id) if self.repo else None
        if not record:
            raise KeyError(f"Approval ID '{approval_id}' not found.")

        if record.status != "PENDING_APPROVAL":
            raise ValueError(f"Approval '{approval_id}' cannot be approved from status '{record.status}'.")

        # Update status
        self.repo.update_status(approval_id, "APPROVED", decided_by=actor_id)

        # Dispatch action in sandbox
        changes = json.loads(record.proposed_changes_json)
        proposal = InterventionProposal(
            intervention_id=record.intervention_id,
            action_type=InterventionType(record.action_type),
            account_id=record.account_id,
            target_date=datetime.utcnow().isoformat(),
            predicted_probability=0.5,
            expected_cost_benefit=1.0,
            title=record.title,
            description=record.description,
            proposed_changes=changes,
            mandatory_human_approval=True,
            is_reversible=True,
            requires_authorization=True,
            idempotency_key=record.idempotency_key,
            status="APPROVED",
        )

        outcome = action_dispatcher.dispatch(proposal)
        final_status = "EXECUTED_IN_SANDBOX" if outcome.status == "EXECUTED_IN_SANDBOX" else "FAILED"
        self.repo.update_status(approval_id, final_status, decided_by=actor_id)

        self.audit.record(
            actor=actor_id,
            account_id=record.account_id,
            action="APPROVE_INTERVENTION",
            status=final_status,
            details={"approval_id": approval_id, "outcome": outcome.model_dump()},
        )

        return {
            "approval_id": approval_id,
            "status": final_status,
            "message": outcome.message,
        }

    def reject(self, approval_id: str, actor_id: str, reason: str = "") -> Dict[str, any]:
        """User or authorized actor rejects a pending intervention."""
        record = self.repo.get(approval_id) if self.repo else None
        if not record:
            raise KeyError(f"Approval ID '{approval_id}' not found.")

        if record.status != "PENDING_APPROVAL":
            raise ValueError(f"Approval '{approval_id}' cannot be rejected from status '{record.status}'.")

        self.repo.update_status(approval_id, "REJECTED", decided_by=actor_id, reason=reason)
        idempotency_store.mark_failed(record.idempotency_key)

        self.audit.record(
            actor=actor_id,
            account_id=record.account_id,
            action="REJECT_INTERVENTION",
            status="REJECTED",
            details={"approval_id": approval_id, "reason": reason},
        )

        return {
            "approval_id": approval_id,
            "status": "REJECTED",
            "message": f"Intervention rejected by {actor_id}.",
        }

    def list_pending_approvals(self, account_id: Optional[str] = None):
        return self.repo.list_pending(account_id) if self.repo else []
