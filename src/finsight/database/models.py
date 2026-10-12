"""SQLAlchemy database models for accounts, transactions, approvals, and audit logs."""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AccountModel(Base):
    __tablename__ = "accounts"

    account_id = Column(String(64), primary_key=True, index=True)
    account_type = Column(String(32), default="PERSONAL")
    currency = Column(String(8), default="BDT")
    available_balance = Column(Float, default=0.0)
    ledger_balance = Column(Float, default=0.0)
    credit_limit = Column(Float, default=0.0)
    has_overdraft = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TransactionModel(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="BDT")
    transaction_type = Column(String(32), nullable=False)
    category = Column(String(64), default="UNCERTAIN")
    description = Column(String(256), default="")
    counterparty = Column(String(128), nullable=True)
    is_internal_transfer = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    balance_after = Column(Float, nullable=True)


class ApprovalModel(Base):
    __tablename__ = "approvals"

    approval_id = Column(String(64), primary_key=True, index=True)
    intervention_id = Column(String(64), index=True, nullable=False)
    account_id = Column(String(64), index=True, nullable=False)
    action_type = Column(String(32), nullable=False)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(32), default="PENDING_APPROVAL")  # PROPOSED, PENDING_APPROVAL, APPROVED, REJECTED, EXPIRED, EXECUTED_IN_SANDBOX, FAILED
    proposed_changes_json = Column(Text, default="{}")
    idempotency_key = Column(String(64), unique=True, index=True, nullable=False)
    requested_by = Column(String(64), default="SYSTEM_AGENT")
    decided_by = Column(String(64), nullable=True)
    decision_reason = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    actor = Column(String(64), nullable=False)
    account_id = Column(String(64), index=True, nullable=False)
    action = Column(String(64), nullable=False)
    policy_version = Column(String(32), default="1.0.0")
    model_version = Column(String(32), default="1.0.0")
    status = Column(String(32), nullable=False)
    details_json = Column(Text, default="{}")
