"""Typed API client connecting the Streamlit frontend to the FastAPI backend."""

import os
from typing import Any, Dict, List, Optional
import httpx

DEFAULT_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class FinsightAPIClient:
    """Client for querying FinSight AI backend services."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, api_key: str = "demo-api-key-finsight"):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-API-Key": api_key,
            "Accept": "application/json",
        }
        self.timeout = 10.0

    def check_health(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}/health", headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    def list_accounts(self) -> List[Dict[str, Any]]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}/api/v1/accounts", headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    def get_account_summary(self, account_id: str) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}/api/v1/accounts/{account_id}/summary", headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    def get_forecast(self, account_id: str, method: str = "probabilistic") -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                f"{self.base_url}/api/v1/accounts/{account_id}/forecast?method={method}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def run_risk_assessment(self, account_id: str) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/api/v1/accounts/{account_id}/risk-assessment",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def get_explanations(self, account_id: str) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                f"{self.base_url}/api/v1/accounts/{account_id}/explanations",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def get_recommendations(self, account_id: str) -> List[Dict[str, Any]]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(
                f"{self.base_url}/api/v1/accounts/{account_id}/recommendations",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def list_pending_approvals(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/approvals/pending"
        if account_id:
            url += f"?account_id={account_id}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    def approve_intervention(self, approval_id: str) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/api/v1/approvals/{approval_id}/approve",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def reject_intervention(self, approval_id: str, reason: str = "User rejected in dashboard") -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/api/v1/approvals/{approval_id}/reject",
                json={"reason": reason},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def get_model_evaluations(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}/api/v1/evaluations/model", headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    def get_policy_evaluations(self) -> Dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}/api/v1/evaluations/policy", headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    def upload_csv(self, file_bytes: bytes, filename: str, currency: str = "BDT", account_type: str = "PERSONAL") -> Dict[str, Any]:
        files = {"file": (filename, file_bytes, "text/csv")}
        data = {"currency": currency, "account_type": account_type}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/api/v1/transactions/upload",
                files=files,
                data=data,
                headers={"X-API-Key": self.headers["X-API-Key"]},
            )
            resp.raise_for_status()
            return resp.json()
