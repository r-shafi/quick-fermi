"""Action dispatcher executing policy-approved interventions strictly in sandbox mode."""

from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel

from finsight.decision.intervention_catalog import InterventionProposal, InterventionType
from finsight.execution.notification_adapter import notification_adapter


class DispatchOutcome(BaseModel):
    dispatch_id: str
    intervention_id: str
    action_type: str
    status: str  # EXECUTED_IN_SANDBOX, FAILED
    executed_at: datetime
    sandbox_details: Dict[str, Any]
    message: str


class SandboxActionDispatcher:
    """Dispatches financial interventions safely into sandbox/simulation."""

    def dispatch(self, proposal: InterventionProposal) -> DispatchOutcome:
        now = datetime.utcnow()
        disp_id = f"DISP_{proposal.intervention_id}"

        if proposal.action_type == InterventionType.INFORM:
            notification_adapter.dispatch(
                account_id=proposal.account_id,
                title=proposal.title,
                message=proposal.description,
                channel="IN_APP",
            )
            return DispatchOutcome(
                dispatch_id=disp_id,
                intervention_id=proposal.intervention_id,
                action_type=proposal.action_type.value,
                status="EXECUTED_IN_SANDBOX",
                executed_at=now,
                sandbox_details={"advisory_displayed": True},
                message="Informational advisory rendered to user.",
            )

        elif proposal.action_type == InterventionType.ALERT:
            notification_adapter.dispatch(
                account_id=proposal.account_id,
                title=proposal.title,
                message=proposal.description,
                channel="IN_APP",
            )
            return DispatchOutcome(
                dispatch_id=disp_id,
                intervention_id=proposal.intervention_id,
                action_type=proposal.action_type.value,
                status="EXECUTED_IN_SANDBOX",
                executed_at=now,
                sandbox_details={"urgent_alert_dispatched": True},
                message="Urgent liquidity alert dispatched via in-app notification.",
            )

        elif proposal.action_type == InterventionType.BUDGET_PROPOSAL:
            return DispatchOutcome(
                dispatch_id=disp_id,
                intervention_id=proposal.intervention_id,
                action_type=proposal.action_type.value,
                status="EXECUTED_IN_SANDBOX",
                executed_at=now,
                sandbox_details={
                    "proposed_reductions": proposal.proposed_changes,
                    "target_savings_bdt": 2500.0,
                    "applied_to_sandbox_budget": True,
                },
                message="Discretionary budget reduction guidelines applied to sandbox profile.",
            )

        elif proposal.action_type == InterventionType.BILL_REVIEW:
            return DispatchOutcome(
                dispatch_id=disp_id,
                intervention_id=proposal.intervention_id,
                action_type=proposal.action_type.value,
                status="EXECUTED_IN_SANDBOX",
                executed_at=now,
                sandbox_details={
                    "bill_extension_reminder_set": True,
                    "biller_details": proposal.proposed_changes,
                },
                message="Bill review reminder and merchant deferral template prepared.",
            )

        elif proposal.action_type == InterventionType.CASHFLOW_SCENARIO:
            return DispatchOutcome(
                dispatch_id=disp_id,
                intervention_id=proposal.intervention_id,
                action_type=proposal.action_type.value,
                status="EXECUTED_IN_SANDBOX",
                executed_at=now,
                sandbox_details={"scenario_evaluated": True, "hypothetical_savings": 5000.0},
                message="Interactive sandbox scenario completed.",
            )

        elif proposal.action_type == InterventionType.HUMAN_REVIEW:
            return DispatchOutcome(
                dispatch_id=disp_id,
                intervention_id=proposal.intervention_id,
                action_type=proposal.action_type.value,
                status="EXECUTED_IN_SANDBOX",
                executed_at=now,
                sandbox_details={"escalated_to_advisor_queue": True},
                message="Account escalated to financial specialist review queue.",
            )

        return DispatchOutcome(
            dispatch_id=disp_id,
            intervention_id=proposal.intervention_id,
            action_type=proposal.action_type.value,
            status="FAILED",
            executed_at=now,
            sandbox_details={},
            message=f"Unknown intervention type {proposal.action_type.value}",
        )


action_dispatcher = SandboxActionDispatcher()
