"""Append-only audit logging service."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from finsight.database.repositories import AuditRepository


class AuditLogger:
    """Provides append-only audit tracking for security and financial actions."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.repo = AuditRepository(db) if db else None
        self._memory_logs: List[Dict[str, Any]] = []

    def record(
        self,
        actor: str,
        account_id: str,
        action: str,
        status: str,
        policy_version: str = "1.0.0",
        model_version: str = "1.0.0",
        details: Optional[Dict[str, Any]] = None,
    ):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "actor": actor,
            "account_id": account_id,
            "action": action,
            "policy_version": policy_version,
            "model_version": model_version,
            "status": status,
            "details": details or {},
        }
        self._memory_logs.append(entry)

        if self.repo:
            try:
                self.repo.log_event(
                    actor=actor,
                    account_id=account_id,
                    action=action,
                    status=status,
                    policy_version=policy_version,
                    model_version=model_version,
                    details=details,
                )
            except Exception:
                pass

    def get_logs_for_account(self, account_id: str) -> List[Dict[str, Any]]:
        if self.repo:
            db_logs = self.repo.list_by_account(account_id)
            if db_logs:
                import json
                return [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "actor": log.actor,
                        "account_id": log.account_id,
                        "action": log.action,
                        "policy_version": log.policy_version,
                        "model_version": log.model_version,
                        "status": log.status,
                        "details": json.loads(log.details_json),
                    }
                    for log in db_logs
                ]
        return [l for l in self._memory_logs if l["account_id"] == account_id]
