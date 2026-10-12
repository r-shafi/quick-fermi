"""Human approval queue management routes."""

import json
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from finsight.api.dependencies import enforce_rate_limit, get_current_user, get_db
from finsight.execution.approval_service import ApprovalService

router = APIRouter(prefix="/api/v1/approvals", tags=["Approvals"])


class DecisionRequest(BaseModel):
    reason: Optional[str] = "User decision via dashboard"


class ApprovalItemResponse(BaseModel):
    approval_id: str
    intervention_id: str
    account_id: str
    action_type: str
    title: str
    description: str
    status: str
    proposed_changes: Dict
    idempotency_key: str
    created_at: str
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None


@router.get("/pending", response_model=List[ApprovalItemResponse])
def list_pending_approvals(
    account_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve all pending interventions awaiting human approval."""
    service = ApprovalService(db)
    records = service.list_pending_approvals(account_id=account_id)
    items = []
    for r in records:
        items.append(
            ApprovalItemResponse(
                approval_id=r.approval_id,
                intervention_id=r.intervention_id,
                account_id=r.account_id,
                action_type=r.action_type,
                title=r.title,
                description=r.description,
                status=r.status,
                proposed_changes=json.loads(r.proposed_changes_json),
                idempotency_key=r.idempotency_key,
                created_at=r.created_at.isoformat(),
                decided_at=r.decided_at.isoformat() if r.decided_at else None,
                decided_by=r.decided_by,
            )
        )
    return items


@router.post("/{approval_id}/approve")
def approve_intervention(
    approval_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Authorize a proposed intervention for sandbox execution."""
    service = ApprovalService(db)
    try:
        outcome = service.approve(approval_id=approval_id, actor_id=user_id)
        return outcome
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{approval_id}/reject")
def reject_intervention(
    approval_id: str,
    body: DecisionRequest = DecisionRequest(),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Reject a proposed intervention and cancel its execution."""
    service = ApprovalService(db)
    try:
        outcome = service.reject(approval_id=approval_id, actor_id=user_id, reason=body.reason or "")
        return outcome
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
