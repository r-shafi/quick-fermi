"""Seed the SQLite database with all 7 synthetic SME/personal accounts, transactions,
pending approval items, and initial audit trail entries.
"""

from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import uuid

from finsight.database.models import AccountModel, ApprovalModel, AuditLogModel, TransactionModel
from finsight.database.repositories import AccountRepository, ApprovalRepository, TransactionRepository
from finsight.database.session import SessionLocal, init_db
from finsight.ingestion.csv_loader import load_transactions_from_csv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def seed_database(reset: bool = False):
    """Seed all synthetic accounts into the local database."""
    print("Initializing database schema...")
    init_db()

    csv_path = PROJECT_ROOT / "data" / "synthetic" / "transactions.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Synthetic transactions file not found at {csv_path}")

    print(f"Loading transactions from {csv_path}...")
    txs, report = load_transactions_from_csv(csv_path)

    # Group transactions by account
    accounts_map = {}
    for tx in txs:
        accounts_map.setdefault(tx.account_id, []).append(tx)

    with SessionLocal() as db:
        acc_repo = AccountRepository(db)
        tx_repo = TransactionRepository(db)
        approval_repo = ApprovalRepository(db)

        # 1. Seed Accounts and Transactions
        for acc_id, acc_txs in accounts_map.items():
            sorted_txs = sorted(acc_txs, key=lambda x: x.timestamp)
            latest_tx = sorted_txs[-1]
            latest_bal = latest_tx.balance_after if latest_tx.balance_after is not None else 50000.0

            acc_type = "SME" if "SME" in acc_id.upper() else "PERSONAL"
            credit_limit = 50000.0 if acc_type == "SME" else 10000.0
            has_overdraft = True if acc_type == "SME" else False

            acc = acc_repo.upsert(
                account_id=acc_id,
                account_type=acc_type,
                currency="BDT",
                available_balance=float(latest_bal),
                ledger_balance=float(latest_bal),
                credit_limit=credit_limit,
                has_overdraft=has_overdraft,
            )

            inserted = tx_repo.bulk_insert(acc_txs)
            print(f"  -> Account {acc_id} ({acc_type}): {len(acc_txs)} transactions, balance: ৳ {latest_bal:,.2f}")

        # 2. Seed realistic Pending Approvals for demonstration
        existing_pending = approval_repo.list_pending()
        if not existing_pending:
            print("Seeding demo pending approval items...")
            demo_approvals = [
                ApprovalModel(
                    approval_id="APP_DEMO_001",
                    intervention_id="INT_REC_DISCOUNT_01",
                    account_id="ACC_005_SME",
                    action_type="RECEIVABLE_ACCELERATION",
                    title="Automated SMS Receivable Discounting & Reminder",
                    description="Offer 1.5% settlement incentive for overdue invoice #INV-881 to accelerate collection by 4 days.",
                    proposed_changes_json=json.dumps({
                        "invoice_id": "INV-881",
                        "customer": "Apex Textile Ltd",
                        "discount_pct": 1.5,
                        "expected_settlement_days": 2,
                        "predicted_probability": 0.68,
                        "expected_cost_benefit": 12450.0,
                        "evidence_summary": [
                            "Invoice #INV-881 (Apex Textile Ltd) overdue past 21-day collection window",
                            "Predicted shortfall probability of 68% against decision boundary of 32%",
                            "Early collection injects ৳ 65,000 liquidity prior to Day 7 payroll",
                        ],
                    }),
                    idempotency_key="idemp_demo_app_001",
                    requested_by="SYSTEM_AGENT",
                    status="PENDING_APPROVAL",
                    created_at=datetime.utcnow(),
                ),
                ApprovalModel(
                    approval_id="APP_DEMO_002",
                    intervention_id="INT_DISC_FREEZE_02",
                    account_id="ACC_005_SME",
                    action_type="EXPENSE_REDUCTION",
                    title="Variable Discretionary Spend Pause (14 Days)",
                    description="Temporarily pause non-essential marketing subscriptions and corporate travel.",
                    proposed_changes_json=json.dumps({
                        "categories": ["DISCRETIONARY", "TRAVEL", "SUBSCRIPTIONS"],
                        "duration_days": 14,
                        "projected_savings": 8200.0,
                        "predicted_probability": 0.68,
                        "expected_cost_benefit": 8200.0,
                        "evidence_summary": [
                            "Discretionary expenditure accounts for 18% of monthly burn",
                            "Essential categories (Payroll, Rent, Utilities) remain 100% untouched",
                            "Preserves ৳ 8,200 liquidity buffer",
                        ],
                    }),
                    idempotency_key="idemp_demo_app_002",
                    requested_by="SYSTEM_AGENT",
                    status="PENDING_APPROVAL",
                    created_at=datetime.utcnow(),
                ),
            ]
            for app_item in demo_approvals:
                db.add(app_item)
            db.commit()

        # 3. Seed initial Hash-Chained Audit Logs
        audit_count = db.query(AuditLogModel).count()
        if audit_count == 0:
            print("Seeding initial immutable audit trail entries...")
            audit_events = [
                ("SYSTEM_BOOT", "ACC_005_SME", "SYSTEM_DAEMON", "INITIALIZE_CORE", "SUCCESS", "Initialized FinSight AI core engine with cost matrix C_FN=5.0, C_FP=1.0"),
                ("DATA_INGESTION", "ACC_005_SME", "ETL_PIPELINE", "LOAD_TRANSACTIONS", "SUCCESS", "Ingested and validated 57 commercial SME ledger records"),
                ("RISK_ASSESSMENT", "ACC_005_SME", "RISK_ENGINE", "PREDICT_SHORTFALL", "SUCCESS", "Evaluated calibrated shortfall probability p=0.68 against threshold τ*=0.32"),
                ("PROPOSAL_DISPATCH", "ACC_005_SME", "POLICY_ENGINE", "PROPOSE_INTERVENTION", "PENDING_APPROVAL", "Dispatched proposal APP_DEMO_001 for human approval"),
            ]
            for event_type, acc_id, actor, action, auth_res, detail in audit_events:
                now_utc = datetime.utcnow()
                log_entry = AuditLogModel(
                    timestamp=now_utc,
                    actor=actor,
                    account_id=acc_id,
                    action=action,
                    policy_version="1.0.0",
                    model_version="1.0.0",
                    status=auth_res,
                    details_json=json.dumps({"event_type": event_type, "details": detail}),
                )
                db.add(log_entry)
            db.commit()

    print("Seeding complete! Database successfully populated.")


if __name__ == "__main__":
    seed_database()
