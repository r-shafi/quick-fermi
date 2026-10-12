"""Integration tests for transaction ingestion and reconciliation API."""

import io
from fastapi.testclient import TestClient
import pytest

from finsight.main import app

client = TestClient(app)


def test_upload_valid_csv():
    csv_content = (
        "transaction_id,account_id,timestamp,amount,currency,transaction_type,category,description,counterparty,is_internal_transfer,is_recurring,balance_after\n"
        "TX_INT_001,ACC_INTEG_01,2024-01-01 09:00:00+06:00,50000.0,BDT,INCOME,SALARY,Salary,Tech Ltd,False,True,50000.0\n"
        "TX_INT_002,ACC_INTEG_01,2024-01-02 12:00:00+06:00,15000.0,BDT,EXPENSE,RENT,Rent,Landlord,False,True,35000.0\n"
    )

    files = {"file": ("test_txs.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(
        "/api/v1/transactions/upload",
        files=files,
        data={"currency": "BDT", "account_type": "PERSONAL"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "ACC_INTEG_01"
    assert data["total_records"] == 2
    assert data["valid_records"] == 2
    assert data["duplicate_records"] == 0
    assert data["has_unsupported_currency"] is False


def test_upload_invalid_file_extension():
    files = {"file": ("test.txt", io.BytesIO(b"dummy data"), "text/plain")}
    response = client.post("/api/v1/transactions/upload", files=files)
    assert response.status_code == 400
    assert "must be a CSV" in response.json()["detail"]


def test_deduplication_handling():
    # Exactly duplicate row with same transaction_id
    csv_content = (
        "transaction_id,account_id,timestamp,amount,currency,transaction_type,category,description,counterparty,is_internal_transfer,is_recurring,balance_after\n"
        "TX_DUP_001,ACC_DUP_01,2024-01-01 09:00:00+06:00,5000.0,BDT,INCOME,SALARY,Salary,Tech Ltd,False,True,5000.0\n"
        "TX_DUP_001,ACC_DUP_01,2024-01-01 09:00:00+06:00,5000.0,BDT,INCOME,SALARY,Salary,Tech Ltd,False,True,5000.0\n"
    )

    files = {"file": ("test_dup.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(
        "/api/v1/transactions/upload",
        files=files,
        data={"currency": "BDT"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 2
    assert data["duplicate_records"] == 1
    assert data["valid_records"] == 1


def test_internal_transfer_reconciliation_flagged():
    csv_content = (
        "transaction_id,account_id,timestamp,amount,currency,transaction_type,category,description,counterparty,is_internal_transfer,is_recurring,balance_after\n"
        "TX_TRF_001,ACC_TRF_01,2024-01-01 09:00:00+06:00,10000.0,BDT,INCOME,SALARY,Salary,Tech Ltd,False,True,10000.0\n"
        "TX_TRF_002,ACC_TRF_01,2024-01-03 10:00:00+06:00,2000.0,BDT,TRANSFER,INTERNAL_TRANSFER,Self-transfer to savings,Savings Acc,True,False,8000.0\n"
    )

    files = {"file": ("test_trf.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post(
        "/api/v1/transactions/upload",
        files=files,
        data={"currency": "BDT"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid_records"] == 2
    assert data["reconciled"] is True
