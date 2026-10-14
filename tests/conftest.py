"""Pytest configuration and test fixtures for FinSight AI."""

from pathlib import Path
import pytest

from finsight.database.models import Base
from finsight.database.session import engine, init_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure database tables are initialized and synthetic accounts seeded for test suite."""
    init_db()

    # Seed ACC_001_STABLE and basic fixtures if needed
    from finsight.database.repositories import AccountRepository, TransactionRepository
    from finsight.database.session import SessionLocal
    from finsight.ingestion.csv_loader import load_transactions_from_csv

    tx_csv = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "transactions.csv"
    if tx_csv.exists():
        txs, report = load_transactions_from_csv(tx_csv)
        with SessionLocal() as db:
            acc_repo = AccountRepository(db)
            tx_repo = TransactionRepository(db)
            for acc_id in ["ACC_001_STABLE", "ACC_005_SME"]:
                acc_txs = [t for t in txs if t.account_id == acc_id]
                if acc_txs:
                    latest = sorted(acc_txs, key=lambda x: x.timestamp)[-1]
                    bal = latest.balance_after if latest.balance_after is not None else 50000.0
                    acc_repo.upsert(acc_id, "SME" if "SME" in acc_id else "PERSONAL", "BDT", available_balance=bal, ledger_balance=bal)
                    tx_repo.bulk_insert(acc_txs)
            db.commit()
    yield
