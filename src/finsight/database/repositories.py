"""Database repository abstraction layer."""

import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from finsight.database.models import AccountModel, ApprovalModel, AuditLogModel, TransactionModel
from finsight.ingestion.schema import ValidatedTransaction


class AccountRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, account_id: str) -> Optional[AccountModel]:
        return self.db.query(AccountModel).filter(AccountModel.account_id == account_id).first()

    def get_all(self) -> List[AccountModel]:
        return self.db.query(AccountModel).all()

    def upsert(
        self,
        account_id: str,
        account_type: str = "PERSONAL",
        currency: str = "BDT",
        available_balance: float = 0.0,
        ledger_balance: float = 0.0,
        credit_limit: float = 0.0,
        has_overdraft: bool = False,
    ) -> AccountModel:
        acc = self.get(account_id)
        if not acc:
            acc = AccountModel(
                account_id=account_id,
                account_type=account_type,
                currency=currency,
                available_balance=available_balance,
                ledger_balance=ledger_balance,
                credit_limit=credit_limit,
                has_overdraft=has_overdraft,
            )
            self.db.add(acc)
        else:
            acc.available_balance = available_balance
            acc.ledger_balance = ledger_balance
            acc.account_type = account_type
            acc.currency = currency
            acc.has_overdraft = has_overdraft
        self.db.commit()
        self.db.refresh(acc)
        return acc


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_account(self, account_id: str) -> List[TransactionModel]:
        return (
            self.db.query(TransactionModel)
            .filter(TransactionModel.account_id == account_id)
            .order_by(TransactionModel.timestamp.asc())
            .all()
        )

    def bulk_insert(self, txs: List[ValidatedTransaction]) -> int:
        inserted = 0
        for tx in txs:
            existing = (
                self.db.query(TransactionModel)
                .filter(TransactionModel.transaction_id == tx.transaction_id)
                .first()
            )
            if not existing:
                model = TransactionModel(
                    transaction_id=tx.transaction_id,
                    account_id=tx.account_id,
                    timestamp=tx.timestamp,
                    amount=tx.amount,
                    currency=tx.currency,
                    transaction_type=tx.transaction_type.value,
                    category=tx.category.value,
                    description=tx.description,
                    counterparty=tx.counterparty,
                    is_internal_transfer=tx.is_internal_transfer,
                    is_recurring=tx.is_recurring,
                    balance_after=tx.balance_after,
                )
                self.db.add(model)
                inserted += 1
        self.db.commit()
        return inserted


class ApprovalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, approval_id: str) -> Optional[ApprovalModel]:
        return self.db.query(ApprovalModel).filter(ApprovalModel.approval_id == approval_id).first()

    def get_by_idempotency_key(self, idemp_key: str) -> Optional[ApprovalModel]:
        return self.db.query(ApprovalModel).filter(ApprovalModel.idempotency_key == idemp_key).first()

    def list_pending(self, account_id: Optional[str] = None) -> List[ApprovalModel]:
        q = self.db.query(ApprovalModel).filter(ApprovalModel.status == "PENDING_APPROVAL")
        if account_id:
            q = q.filter(ApprovalModel.account_id == account_id)
        return q.order_by(ApprovalModel.created_at.desc()).all()

    def list_all(self, account_id: Optional[str] = None) -> List[ApprovalModel]:
        q = self.db.query(ApprovalModel)
        if account_id:
            q = q.filter(ApprovalModel.account_id == account_id)
        return q.order_by(ApprovalModel.created_at.desc()).all()

    def create(
        self,
        approval_id: str,
        intervention_id: str,
        account_id: str,
        action_type: str,
        title: str,
        description: str,
        proposed_changes: Dict,
        idempotency_key: str,
        status: str = "PENDING_APPROVAL",
    ) -> ApprovalModel:
        model = ApprovalModel(
            approval_id=approval_id,
            intervention_id=intervention_id,
            account_id=account_id,
            action_type=action_type,
            title=title,
            description=description,
            proposed_changes_json=json.dumps(proposed_changes),
            idempotency_key=idempotency_key,
            status=status,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model

    def update_status(
        self,
        approval_id: str,
        new_status: str,
        decided_by: str,
        reason: Optional[str] = None,
    ) -> Optional[ApprovalModel]:
        app = self.get(approval_id)
        if not app:
            return None
        app.status = new_status
        app.decided_by = decided_by
        app.decision_reason = reason
        app.decided_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(app)
        return app


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def log_event(
        self,
        actor: str,
        account_id: str,
        action: str,
        status: str,
        policy_version: str = "1.0.0",
        model_version: str = "1.0.0",
        details: Optional[Dict] = None,
    ) -> AuditLogModel:
        log = AuditLogModel(
            actor=actor,
            account_id=account_id,
            action=action,
            policy_version=policy_version,
            model_version=model_version,
            status=status,
            details_json=json.dumps(details or {}),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_by_account(self, account_id: str, limit: int = 50) -> List[AuditLogModel]:
        return (
            self.db.query(AuditLogModel)
            .filter(AuditLogModel.account_id == account_id)
            .order_by(AuditLogModel.timestamp.desc())
            .limit(limit)
            .all()
        )
