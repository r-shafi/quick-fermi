"""Integration tests for the complete risk, forecast, explanation, and recommendation pipeline."""

from fastapi.testclient import TestClient
import pytest

from finsight.main import app

client = TestClient(app)


def test_account_summary_api():
    response = client.get("/api/v1/accounts/ACC_001_STABLE/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "ACC_001_STABLE"
    assert data["currency"] == "BDT"
    assert data["total_transactions"] > 0
    assert data["available_balance"] > 0.0


def test_cashflow_forecast_api():
    # Test probabilistic forecast
    response_prob = client.get("/api/v1/accounts/ACC_001_STABLE/forecast?method=probabilistic")
    assert response_prob.status_code == 200
    data_prob = response_prob.json()
    assert data_prob["account_id"] == "ACC_001_STABLE"
    assert len(data_prob["daily_intervals"]) > 0

    # Test deterministic forecast
    response_det = client.get("/api/v1/accounts/ACC_001_STABLE/forecast?method=deterministic")
    assert response_det.status_code == 200
    data_det = response_det.json()
    assert data_det["account_id"] == "ACC_001_STABLE"
    assert "7" in data_det["horizons"] or 7 in data_det["horizons"]


def test_risk_assessment_and_shap_explanations():
    response = client.post("/api/v1/accounts/ACC_001_STABLE/risk-assessment")
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "ACC_001_STABLE"
    assert "raw_probability" in data
    assert "calibrated_probability" in data
    assert "decision_threshold" in data
    assert "risk_level" in data
    assert "explanation" in data

    # Check SHAP explanation details
    explanation = data["explanation"]
    if explanation:
        assert "top_risk_drivers" in explanation
        assert "top_risk_mitigators" in explanation
        assert "deterministic_narrative" in explanation
        assert "limitations" in explanation


def test_recommendations_expected_cost_ranking():
    response = client.get("/api/v1/accounts/ACC_001_STABLE/recommendations")
    assert response.status_code == 200
    proposals = response.json()
    assert isinstance(proposals, list)
    assert len(proposals) > 0

    for prop in proposals:
        assert "intervention_id" in prop
        assert "action_type" in prop
        assert "expected_cost_benefit" in prop
        assert "mandatory_human_approval" in prop
        assert "idempotency_key" in prop
