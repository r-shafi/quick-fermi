"""FinSight AI — Extended Typed API Client.

Connects the Streamlit frontend to the FastAPI backend with typed
methods for all 17 dashboard pages.
"""

import os
from typing import Any, Dict, List, Optional
import httpx

DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEFAULT_API_KEY = os.getenv("FINSIGHT_API_KEY", "demo-api-key-finsight")


class FinsightAPIClient:
    """Typed client for all FinSight AI backend services."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, api_key: str = DEFAULT_API_KEY):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-API-Key": api_key,
            "Accept": "application/json",
        }
        self.timeout = 30.0

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.get(f"{self.base_url}{path}", headers=self.headers, params=params or {})
            r.raise_for_status()
            return r.json()

    def _post(self, path: str, json: Optional[Dict] = None, files: Optional[Dict] = None, data: Optional[Dict] = None) -> Any:
        with httpx.Client(timeout=self.timeout) as c:
            if files:
                r = c.post(f"{self.base_url}{path}", headers={"X-API-Key": self.headers["X-API-Key"]}, files=files, data=data)
            else:
                r = c.post(f"{self.base_url}{path}", headers=self.headers, json=json)
            r.raise_for_status()
            return r.json()

    # ── Health ─────────────────────────────────────────────────────────────────
    def check_health(self) -> Dict[str, Any]:
        return self._get("/health")

    def get_health(self) -> Dict[str, Any]:
        return self.check_health()

    # ── Accounts ───────────────────────────────────────────────────────────────
    def list_accounts(self) -> List[Dict[str, Any]]:
        return self._get("/api/v1/accounts")

    def get_account_summary(self, account_id: str) -> Dict[str, Any]:
        return self._get(f"/api/v1/accounts/{account_id}/summary")

    # ── Transactions ───────────────────────────────────────────────────────────
    def list_transactions(
        self,
        account_id: str,
        page: int = 1,
        page_size: int = 50,
        category: Optional[str] = None,
        tx_type: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "page_size": page_size}
        if category:
            params["category"] = category
        if tx_type:
            params["tx_type"] = tx_type
        if search:
            params["search"] = search
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return self._get(f"/api/v1/accounts/{account_id}/transactions", params=params)

    def get_reconciliation(self, account_id: str) -> Dict[str, Any]:
        return self._get(f"/api/v1/accounts/{account_id}/reconciliation")

    def upload_csv(
        self,
        file_bytes: bytes,
        filename: str,
        currency: str = "BDT",
        account_type: str = "PERSONAL",
    ) -> Dict[str, Any]:
        files = {"file": (filename, file_bytes, "text/csv")}
        data = {"currency": currency, "account_type": account_type}
        return self._post("/api/v1/transactions/upload", files=files, data=data)

    def validate_csv_dry_run(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Validate CSV schema without ingesting (dry run)."""
        files = {"file": (filename, file_bytes, "text/csv")}
        return self._post("/api/v1/data/validate-csv", files=files)

    # ── Forecasts ─────────────────────────────────────────────────────────────
    def get_forecast(self, account_id: str, method: str = "probabilistic") -> Dict[str, Any]:
        return self._get(f"/api/v1/accounts/{account_id}/forecast", params={"method": method})

    # ── Risk ──────────────────────────────────────────────────────────────────
    def run_risk_assessment(self, account_id: str) -> Dict[str, Any]:
        return self._post(f"/api/v1/accounts/{account_id}/risk-assessment")

    def get_explanations(self, account_id: str) -> Dict[str, Any]:
        return self._get(f"/api/v1/accounts/{account_id}/explanations")

    # ── Recommendations ───────────────────────────────────────────────────────
    def get_recommendations(self, account_id: str) -> List[Dict[str, Any]]:
        return self._get(f"/api/v1/accounts/{account_id}/recommendations")

    # ── Approvals ─────────────────────────────────────────────────────────────
    def list_pending_approvals(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {}
        if account_id:
            params["account_id"] = account_id
        return self._get("/api/v1/approvals/pending", params=params)

    def approve_intervention(self, approval_id: str) -> Dict[str, Any]:
        return self._post(f"/api/v1/approvals/{approval_id}/approve")

    def reject_intervention(self, approval_id: str, reason: str = "User rejected in dashboard") -> Dict[str, Any]:
        return self._post(f"/api/v1/approvals/{approval_id}/reject", json={"reason": reason})

    # ── Scenario simulation ───────────────────────────────────────────────────
    def run_scenario(
        self,
        account_id: str,
        delayed_receipt_days: int = 0,
        receipt_amount_factor: float = 1.0,
        supplier_invoice_factor: float = 1.0,
        payroll_date_offset: int = 0,
        discretionary_expense_factor: float = 1.0,
    ) -> Dict[str, Any]:
        payload = {
            "delayed_receipt_days": delayed_receipt_days,
            "receipt_amount_factor": receipt_amount_factor,
            "supplier_invoice_factor": supplier_invoice_factor,
            "payroll_date_offset": payroll_date_offset,
            "discretionary_expense_factor": discretionary_expense_factor,
        }
        return self._post(f"/api/v1/accounts/{account_id}/scenario", json=payload)

    # ── Evaluations / Model Lab ───────────────────────────────────────────────
    def get_model_evaluations(self) -> Dict[str, Any]:
        return self._get("/api/v1/evaluations/model")

    def get_policy_evaluations(self) -> Dict[str, Any]:
        return self._get("/api/v1/evaluations/policy")

    def get_full_model_metrics(self) -> Dict[str, Any]:
        """Extended model comparison including PR/ROC curves and calibration."""
        return self._get("/api/v1/evaluations/model/full")

    # ── Data quality ──────────────────────────────────────────────────────────
    def get_data_quality_report(self, account_id: str) -> Dict[str, Any]:
        return self._get(f"/api/v1/data/quality-report/{account_id}")

    def get_synthetic_profiles(self) -> List[Dict[str, Any]]:
        return self._get("/api/v1/data/synthetic-profiles")

    # ── Audit ─────────────────────────────────────────────────────────────────
    def list_audit_events(
        self,
        account_id: Optional[str] = None,
        event_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "page_size": page_size}
        if account_id:
            params["account_id"] = account_id
        if event_type:
            params["event_type"] = event_type
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return self._get("/api/v1/audit/events", params=params)

    def get_audit_timeline(self, account_id: str) -> List[Dict[str, Any]]:
        return self._get(f"/api/v1/audit/timeline/{account_id}")

    # ── Security ──────────────────────────────────────────────────────────────
    def get_security_posture(self) -> Dict[str, Any]:
        return self._get("/api/v1/security/posture")

    def run_security_tests(self) -> Dict[str, Any]:
        return self._post("/api/v1/security/run-tests")

    def get_threat_model(self) -> List[Dict[str, Any]]:
        return self._get("/api/v1/security/threats")

    # ── Drift ─────────────────────────────────────────────────────────────────
    def get_drift_report(self, account_id: str) -> Dict[str, Any]:
        return self._get(f"/api/v1/drift/report/{account_id}")

    def get_model_history(self) -> List[Dict[str, Any]]:
        return self._get("/api/v1/drift/model-history")

    # ── Competition evidence ───────────────────────────────────────────────────
    def get_competition_evidence(self) -> Dict[str, Any]:
        return self._get("/api/v1/competition/evidence")

    def get_competition_readiness(self) -> Dict[str, Any]:
        return self._get("/api/v1/competition/readiness")

    def get_competition_documents(self) -> List[Dict[str, Any]]:
        return self._get("/api/v1/competition/documents")

    # ── Settings ──────────────────────────────────────────────────────────────
    def get_settings(self) -> Dict[str, Any]:
        return self._get("/api/v1/settings")

    def update_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/api/v1/settings", json=settings)
