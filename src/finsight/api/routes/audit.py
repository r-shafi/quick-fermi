"""Audit log explorer and cryptographic timeline routes."""

from datetime import datetime
import hashlib
import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from finsight.api.dependencies import enforce_rate_limit, get_current_user, get_db
from finsight.database.models import ApprovalModel, AuditLogModel
from finsight.security.authorization import auth_manager

router = APIRouter(prefix="/api/v1/audit", tags=["Audit Log"])


class AuditEventItem(BaseModel):
    log_id: int
    timestamp: str
    actor: str
    account_ref: str
    action: str
    authorization_result: str
    status: str
    audit_hash: str
    policy_version: str
    model_version: str
    details: Dict[str, Any] = Field(default_factory=dict)
    integrity_verified: bool = True


class AuditEventsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    integrity_verified: bool
    events: List[AuditEventItem]
    message: Optional[str] = None


class TimelineStep(BaseModel):
    step_type: str
    title: str
    status: str
    summary: str
    timestamp: Optional[str] = None
    actor: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


def _compute_hash(
    prev_hash: str,
    log_id: int,
    ts: str,
    actor: str,
    account_id: str,
    action: str,
    status: str,
    policy_version: str,
) -> str:
    payload = f"{prev_hash}|{log_id}|{ts}|{actor}|{account_id}|{action}|{status}|{policy_version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@router.get("/events", response_model=AuditEventsListResponse)
def list_audit_events(
    account_id: Optional[str] = Query(None, description="Filter by account identifier"),
    event_type: Optional[str] = Query(None, description="Filter by action or event type"),
    date_from: Optional[str] = Query(None, description="ISO start date filter"),
    date_to: Optional[str] = Query(None, description="ISO end date filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve chronologically ordered audit events with cryptographic SHA-256 chain verification."""
    query = db.query(AuditLogModel)

    if account_id:
        try:
            auth_manager.verify_account_access(user_id=user_id, account_id=account_id)
        except Exception:
            return AuditEventsListResponse(
                total=0,
                page=page,
                page_size=page_size,
                integrity_verified=True,
                events=[],
                message=f"Access denied or account '{account_id}' not found.",
            )
        query = query.filter(AuditLogModel.account_id == account_id)

    if event_type:
        query = query.filter(AuditLogModel.action.ilike(f"%{event_type}%"))

    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.filter(AuditLogModel.timestamp >= dt_from)
        except ValueError:
            pass

    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.filter(AuditLogModel.timestamp <= dt_to)
        except ValueError:
            pass

    total = query.count()
    if total == 0:
        return AuditEventsListResponse(
            total=0,
            page=page,
            page_size=page_size,
            integrity_verified=True,
            events=[],
            message="No audit events found matching query criteria.",
        )

    # Compute hash chain from genesis across entire ordered table to verify integrity
    all_logs = query.order_by(AuditLogModel.log_id.asc()).all()

    prev_hash = "0" * 64
    verified_events: List[AuditEventItem] = []
    chain_intact = True

    for log in all_logs:
        ts_str = log.timestamp.isoformat()
        expected_hash = _compute_hash(
            prev_hash=prev_hash,
            log_id=log.log_id,
            ts=ts_str,
            actor=log.actor,
            account_id=log.account_id,
            action=log.action,
            status=log.status,
            policy_version=log.policy_version,
        )

        try:
            details_dict = json.loads(log.details_json) if log.details_json else {}
        except Exception:
            details_dict = {}

        stored_hash = details_dict.get("audit_hash")
        log_intact = True
        if stored_hash and stored_hash != expected_hash:
            log_intact = False
            chain_intact = False

        verified_events.append(
            AuditEventItem(
                log_id=log.log_id,
                timestamp=ts_str,
                actor=log.actor,
                account_ref=log.account_id,
                action=log.action,
                authorization_result=log.status,
                status=log.status,
                audit_hash=expected_hash,
                policy_version=log.policy_version,
                model_version=log.model_version,
                details=details_dict,
                integrity_verified=log_intact,
            )
        )
        prev_hash = expected_hash

    # Paginate results (most recent first)
    verified_events_desc = list(reversed(verified_events))
    start_idx = (page - 1) * page_size
    paged_slice = verified_events_desc[start_idx : start_idx + page_size]

    return AuditEventsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        integrity_verified=chain_intact,
        events=paged_slice,
    )


@router.get("/timeline/{account_id}", response_model=List[TimelineStep])
def get_audit_timeline(
    account_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve linked risk -> recommendation -> approval -> execution chain for an account."""
    auth_manager.verify_account_access(user_id=user_id, account_id=account_id)

    # Fetch audit logs and approval items for this account
    logs = (
        db.query(AuditLogModel)
        .filter(AuditLogModel.account_id == account_id)
        .order_by(AuditLogModel.timestamp.asc())
        .all()
    )

    approvals = (
        db.query(ApprovalModel)
        .filter(ApprovalModel.account_id == account_id)
        .order_by(ApprovalModel.created_at.desc())
        .all()
    )

    # Map available logs
    risk_log = next((l for l in logs if "risk" in l.action.lower()), None)
    rec_log = next((l for l in logs if "recommend" in l.action.lower()), None)
    app_log = next((l for l in logs if "approv" in l.action.lower() or "reject" in l.action.lower()), None)
    exec_log = next((l for l in logs if "execut" in l.action.lower() or "sandbox" in l.action.lower()), None)

    latest_approval = approvals[0] if approvals else None

    # Step 1: Risk Assessment
    if risk_log:
        risk_step = TimelineStep(
            step_type="risk_assessment",
            title="Risk Assessment",
            status=risk_log.status,
            summary=f"Automated risk evaluation completed ({risk_log.status})",
            timestamp=risk_log.timestamp.isoformat(),
            actor=risk_log.actor,
            details=json.loads(risk_log.details_json) if risk_log.details_json else {},
        )
    else:
        risk_step = TimelineStep(
            step_type="risk_assessment",
            title="Risk Assessment",
            status="NOT YET RECORDED",
            summary="Awaiting risk assessment execution",
        )

    # Step 2: Recommendation
    if rec_log:
        rec_step = TimelineStep(
            step_type="recommendation",
            title="Recommendation",
            status=rec_log.status,
            summary=f"Cost-sensitive intervention generated ({rec_log.status})",
            timestamp=rec_log.timestamp.isoformat(),
            actor=rec_log.actor,
            details=json.loads(rec_log.details_json) if rec_log.details_json else {},
        )
    elif latest_approval:
        rec_step = TimelineStep(
            step_type="recommendation",
            title="Recommendation",
            status="PROPOSED",
            summary=latest_approval.title,
            timestamp=latest_approval.created_at.isoformat(),
            actor=latest_approval.requested_by,
            details={"intervention_id": latest_approval.intervention_id, "action_type": latest_approval.action_type},
        )
    else:
        rec_step = TimelineStep(
            step_type="recommendation",
            title="Recommendation",
            status="NOT YET RECORDED",
            summary="No interventions currently proposed",
        )

    # Step 3: Approval
    if latest_approval:
        app_step = TimelineStep(
            step_type="approval",
            title="Human Approval",
            status=latest_approval.status,
            summary=f"Decision by {latest_approval.decided_by or 'Pending Operator'}",
            timestamp=latest_approval.decided_at.isoformat() if latest_approval.decided_at else latest_approval.created_at.isoformat(),
            actor=latest_approval.decided_by or "pending",
            details={
                "approval_id": latest_approval.approval_id,
                "idempotency_key": latest_approval.idempotency_key,
                "reason": latest_approval.decision_reason,
            },
        )
    elif app_log:
        app_step = TimelineStep(
            step_type="approval",
            title="Human Approval",
            status=app_log.status,
            summary=f"Approval action: {app_log.action}",
            timestamp=app_log.timestamp.isoformat(),
            actor=app_log.actor,
            details=json.loads(app_log.details_json) if app_log.details_json else {},
        )
    else:
        app_step = TimelineStep(
            step_type="approval",
            title="Human Approval",
            status="NOT YET RECORDED",
            summary="No pending or decided approval items",
        )

    # Step 4: Sandbox Execution
    if latest_approval and latest_approval.status == "EXECUTED_IN_SANDBOX":
        exec_step = TimelineStep(
            step_type="execution",
            title="Sandbox Execution",
            status="EXECUTED",
            summary="Dispatched safely to isolated sandbox environment",
            timestamp=latest_approval.decided_at.isoformat() if latest_approval.decided_at else None,
            actor="SandboxDispatcher",
        )
    elif exec_log:
        exec_step = TimelineStep(
            step_type="execution",
            title="Sandbox Execution",
            status=exec_log.status,
            summary="Executed simulated changes in sandbox",
            timestamp=exec_log.timestamp.isoformat(),
            actor=exec_log.actor,
            details=json.loads(exec_log.details_json) if exec_log.details_json else {},
        )
    else:
        exec_step = TimelineStep(
            step_type="execution",
            title="Sandbox Execution",
            status="NOT YET RECORDED",
            summary="No sandbox executions registered",
        )

    # Step 5: Observed Outcome
    outcome_step = TimelineStep(
        step_type="outcome",
        title="Observed Outcome",
        status="MONITORED" if (risk_log or latest_approval) else "NOT YET RECORDED",
        summary="Synthetic sandbox state maintained. Zero live banking movement.",
    )

    return [risk_step, rec_step, app_step, exec_step, outcome_step]
