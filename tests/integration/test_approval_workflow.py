"""Integration tests for the human approval workflow, sandbox execution, and audit log."""

from fastapi.testclient import TestClient
import pytest

from finsight.database.models import ApprovalModel, AuditLogModel
from finsight.database.session import SessionLocal
from finsight.decision.intervention_catalog import InterventionProposal, InterventionType
from finsight.execution.approval_service import ApprovalService
from finsight.main import app

client = TestClient(app)


import uuid

@pytest.fixture
def test_proposal():
    uid = uuid.uuid4().hex[:8]
    return InterventionProposal(
        intervention_id=f"INT_TEST_APP_{uid}",
        action_type=InterventionType.BUDGET_PROPOSAL,
        account_id="ACC_001_STABLE",
        target_date="2024-02-01T00:00:00",
        predicted_probability=0.75,
        expected_cost_benefit=1.85,
        title="Reduce Discretionary Spending",
        description="Suggested voluntary discretionary cut to preserve liquidity",
        evidence_summary=["Shortfall risk 75%"],
        proposed_changes={"category": "entertainment", "suggested_reduction_pct": 20.0},
        mandatory_human_approval=True,
        is_reversible=True,
        requires_authorization=True,
        idempotency_key=f"idemp_test_workflow_{uid}",
    )


def test_approval_lifecycle_and_idempotency(test_proposal):
    with SessionLocal() as db:
        service = ApprovalService(db)
        # 1. Submit proposal
        res = service.submit_proposal(test_proposal)
        approval_id = res["approval_id"]
        assert res["status"] == "PENDING_APPROVAL"

    # 2. Check pending endpoint
    resp_pending = client.get("/api/v1/approvals/pending")
    assert resp_pending.status_code == 200
    pending_items = resp_pending.json()
    assert any(item["approval_id"] == approval_id for item in pending_items)

    # 3. Approve intervention
    resp_approve = client.post(f"/api/v1/approvals/{approval_id}/approve")
    assert resp_approve.status_code == 200
    outcome = resp_approve.json()
    assert outcome["approval_id"] == approval_id
    assert outcome["status"] in ("APPROVED", "EXECUTED_IN_SANDBOX")

    # 4. Idempotency / state machine: approving already executed gives 400
    resp_approve_again = client.post(f"/api/v1/approvals/{approval_id}/approve")
    assert resp_approve_again.status_code == 400

    # 5. Verify audit log entries exist for account
    with SessionLocal() as db:
        audit_entries = db.query(AuditLogModel).filter(
            AuditLogModel.account_id == "ACC_001_STABLE"
        ).all()
        assert len(audit_entries) >= 1
        actions = [e.action for e in audit_entries]
        assert "PROPOSE_INTERVENTION" in actions or "APPROVE_INTERVENTION" in actions


def test_rejection_lifecycle():
    uid = uuid.uuid4().hex[:8]
    proposal = InterventionProposal(
        intervention_id=f"INT_TEST_REJ_{uid}",
        action_type=InterventionType.BILL_REVIEW,
        account_id="ACC_001_STABLE",
        target_date="2024-02-01T00:00:00",
        predicted_probability=0.60,
        expected_cost_benefit=1.20,
        title="Biller Review",
        description="Review payment extension",
        evidence_summary=["Risk 60%"],
        proposed_changes={"category": "bill_timing", "request_extension_days": 3},
        mandatory_human_approval=True,
        is_reversible=True,
        requires_authorization=True,
        idempotency_key=f"idemp_test_reject_{uid}",
    )

    with SessionLocal() as db:
        service = ApprovalService(db)
        res = service.submit_proposal(proposal)
        approval_id = res["approval_id"]

    # Reject intervention
    resp_reject = client.post(
        f"/api/v1/approvals/{approval_id}/reject",
        json={"reason": "User chose not to negotiate with biller"},
    )
    assert resp_reject.status_code == 200
    outcome = resp_reject.json()
    assert outcome["approval_id"] == approval_id
    assert outcome["status"] == "REJECTED"

    # Verify no longer in pending list
    resp_pending = client.get("/api/v1/approvals/pending")
    assert resp_pending.status_code == 200
    pending_items = resp_pending.json()
    assert not any(item["approval_id"] == approval_id for item in pending_items)
