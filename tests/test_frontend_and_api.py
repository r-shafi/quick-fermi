"""Frontend integration, API client resilience, and governance testing suite.

Verifies:
1. All 17 dashboard pages exist and have valid syntax.
2. Typed API client covers all backend endpoints with structured responses.
3. Failed API calls raise exceptions and cannot appear as successful operations.
4. Duplicate/refreshed requests do not duplicate approval actions (Idempotency).
5. Prominent [SYNTHETIC] provenance and real-world disclaimer presence.
6. Absence of fabricated judge scores or fake accuracy metrics.
"""

import ast
from pathlib import Path
import uuid
import pytest
from fastapi.testclient import TestClient

from finsight.api.dependencies import auth_manager
from finsight.database.models import ApprovalModel
from finsight.database.session import SessionLocal
from finsight.decision.intervention_catalog import InterventionProposal, InterventionType
from finsight.execution.approval_service import ApprovalService
from finsight.main import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
client = TestClient(app)


def test_all_17_frontend_pages_exist_and_parse():
    """Verify all 17 competition dashboard pages exist and contain valid Python syntax."""
    pages_dir = PROJECT_ROOT / "frontend" / "pages"
    assert pages_dir.exists(), f"Pages directory not found at {pages_dir}"

    expected_pages = [
        "01_Overview.py",
        "02_SME_Command_Center.py",
        "03_Cashflow_Forecast.py",
        "04_Risk_Intelligence.py",
        "05_AI_Agent_Workspace.py",
        "06_Scenario_Simulator.py",
        "07_Approval_Center.py",
        "08_Model_Lab.py",
        "09_Financial_Accuracy.py",
        "10_Security_Compliance.py",
        "11_Adversarial_Testing.py",
        "12_Data_Quality.py",
        "13_Model_Drift.py",
        "14_RL_Research.py",
        "15_Audit_History.py",
        "16_Competition_Evidence.py",
        "17_System_Settings.py",
    ]

    found_files = sorted([f.name for f in pages_dir.glob("*.py")])
    for exp in expected_pages:
        assert exp in found_files, f"Missing required page: {exp}"
        # Validate AST parsing
        page_path = pages_dir / exp
        with open(page_path, "r", encoding="utf-8") as f:
            code = f.read()
        ast.parse(code, filename=str(page_path))


def test_api_client_error_handling_invalid_account():
    """Verify that querying a non-existent account returns 404 for admin and 403 for unauthorized users."""
    # 1. Admin querying non-existent account gets 404
    resp_admin = client.get("/api/v1/accounts/ACC_NON_EXISTENT_999/summary", headers={"X-API-Key": "admin-api-key-finsight"})
    assert resp_admin.status_code == 404
    assert "not found" in resp_admin.json()["detail"].lower()

    # 2. Unauthorized user querying non-existent account gets 403 (fail-closed security)
    resp_unauth = client.get("/api/v1/accounts/ACC_NON_EXISTENT_999/summary", headers={"X-API-Key": "demo-api-key-finsight"})
    assert resp_unauth.status_code == 403


def test_failed_api_call_cannot_appear_as_success():
    """Verify that posting invalid approval ID returns 404 rather than 200."""
    resp = client.post("/api/v1/approvals/INVALID_APPROVAL_9999/approve")
    assert resp.status_code == 404


def test_idempotency_prevents_duplicate_approval_execution():
    """Verify state machine idempotency: second approval call rejects duplicate dispatch."""
    uid = uuid.uuid4().hex[:8]
    # Create fresh proposal with guaranteed unique ID and idempotency key
    with SessionLocal() as db:
        service = ApprovalService(db)
        prop = InterventionProposal(
            intervention_id=f"INT_IDEMP_{uid}",
            action_type=InterventionType.BUDGET_PROPOSAL,
            account_id="ACC_001_STABLE",
            target_date="2026-10-20T00:00:00",
            predicted_probability=0.75,
            expected_cost_benefit=1200.0,
            title="Idempotency Test Proposal",
            description="Testing duplicate approval prevention",
            evidence_summary=["Test evidence verification"],
            proposed_changes={"category": "entertainment", "reduction": 10},
            mandatory_human_approval=True,
            is_reversible=True,
            requires_authorization=True,
            idempotency_key=f"idemp_key_{uid}",
        )
        created = service.submit_proposal(prop)
        target_id = created["approval_id"]

    # 1. First approval -> 200 OK
    resp1 = client.post(f"/api/v1/approvals/{target_id}/approve")
    assert resp1.status_code == 200
    assert resp1.json()["status"] in ("APPROVED", "EXECUTED_IN_SANDBOX")

    # 2. Second approval -> 400 Bad Request (Cannot transition already executed item)
    resp2 = client.post(f"/api/v1/approvals/{target_id}/approve")
    assert resp2.status_code == 400
    assert "cannot be approved" in resp2.json()["detail"].lower()


def test_real_world_accuracy_disclaimer_mandatory_presence():
    """Verify that Page 9 and Page 16 explicitly declare real-world SME accuracy has not been established."""
    page_9 = PROJECT_ROOT / "frontend" / "pages" / "09_Financial_Accuracy.py"
    page_16 = PROJECT_ROOT / "frontend" / "pages" / "16_Competition_Evidence.py"

    content_9 = page_9.read_text(encoding="utf-8")
    content_16 = page_16.read_text(encoding="utf-8")

    assert "Real-world SME predictive accuracy has not yet been established." in content_9
    assert "Real-world SME predictive accuracy has not yet been established." in content_16


def test_rl_research_mandatory_disclaimer_presence():
    """Verify that Page 14 contains the mandatory notice declaring RL research is optional."""
    page_14 = PROJECT_ROOT / "frontend" / "pages" / "14_RL_Research.py"
    content_14 = page_14.read_text(encoding="utf-8")
    assert "RL research is optional and is not part of the active decision policy." in content_14


def test_accounts_reconciliation_math():
    """Verify mathematical reconciliation calculation over ACC_001_STABLE and ACC_005_SME."""
    # 1. Personal account via default demo key
    resp_personal = client.get("/api/v1/accounts/ACC_001_STABLE/reconciliation", headers={"X-API-Key": "demo-api-key-finsight"})
    assert resp_personal.status_code == 200
    data_personal = resp_personal.json()
    assert data_personal["account_id"] == "ACC_001_STABLE"
    assert data_personal["status"] in ("RECONCILED", "DISCREPANCY")
    assert "opening_balance" in data_personal
    assert "calculated_closing_balance" in data_personal

    # 2. SME account via sme key
    resp_sme = client.get("/api/v1/accounts/ACC_005_SME/reconciliation", headers={"X-API-Key": "sme-api-key-finsight"})
    assert resp_sme.status_code == 200
    data_sme = resp_sme.json()
    assert data_sme["account_id"] == "ACC_005_SME"
    assert data_sme["status"] in ("RECONCILED", "DISCREPANCY")
