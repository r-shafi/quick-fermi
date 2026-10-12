"""Risk assessment and SHAP explainability routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from finsight.agentic_core.graph import FinsightAgentGraph
from finsight.api.dependencies import enforce_rate_limit, get_db, verify_account_ownership
from finsight.api.routes.forecasts import _to_validated_transactions
from finsight.database.repositories import AccountRepository, TransactionRepository
from finsight.ml_core.predict import RiskAssessmentResult, RiskPredictor

router = APIRouter(prefix="/api/v1/accounts", tags=["Risk & Explanations"])

_agent_graph = FinsightAgentGraph()


@router.post("/{account_id}/risk-assessment", response_model=RiskAssessmentResult)
def run_risk_assessment(
    account_id: str,
    user_id: str = Depends(verify_account_ownership),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Trigger cost-sensitive shortfall risk evaluation and SHAP explainability pipeline."""
    acc_repo = AccountRepository(db)
    acc = acc_repo.get(account_id)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found.",
        )

    tx_repo = TransactionRepository(db)
    db_txs = tx_repo.list_by_account(account_id)
    txs = _to_validated_transactions(db_txs)

    now_dt = datetime.now(ZoneInfo("Asia/Dhaka"))

    exec_result = _agent_graph.run(
        account_id=account_id,
        transactions=txs,
        snapshot_dt=now_dt,
        current_balance=acc.available_balance,
        is_sme=(acc.account_type == "SME"),
    )

    return exec_result.risk_assessment


@router.get("/{account_id}/explanations")
def get_risk_explanations(
    account_id: str,
    user_id: str = Depends(verify_account_ownership),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve verified SHAP contributions and evidence narrative for the account."""
    acc_repo = AccountRepository(db)
    acc = acc_repo.get(account_id)
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_id}' not found.",
        )

    tx_repo = TransactionRepository(db)
    db_txs = tx_repo.list_by_account(account_id)
    txs = _to_validated_transactions(db_txs)

    now_dt = datetime.now(ZoneInfo("Asia/Dhaka"))

    exec_result = _agent_graph.run(
        account_id=account_id,
        transactions=txs,
        snapshot_dt=now_dt,
        current_balance=acc.available_balance,
        is_sme=(acc.account_type == "SME"),
    )

    if not exec_result.risk_assessment.explanation:
        return {
            "status": "NOT_AVAILABLE",
            "message": "Model explanation not available for this account state.",
            "probability": exec_result.risk_assessment.calibrated_probability,
            "threshold": exec_result.risk_assessment.decision_threshold,
        }

    return exec_result.risk_assessment.explanation.model_dump()
