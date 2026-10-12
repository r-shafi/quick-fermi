"""Financial recommendations and intervention proposals API endpoints."""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from finsight.agentic_core.graph import FinsightAgentGraph
from finsight.api.dependencies import enforce_rate_limit, get_db, verify_account_ownership
from finsight.api.routes.forecasts import _to_validated_transactions
from finsight.database.repositories import AccountRepository, TransactionRepository
from finsight.decision.intervention_catalog import InterventionProposal
from finsight.execution.approval_service import ApprovalService

router = APIRouter(prefix="/api/v1/accounts", tags=["Recommendations"])

_agent_graph = FinsightAgentGraph()


@router.get("/{account_id}/recommendations", response_model=List[InterventionProposal])
def get_account_recommendations(
    account_id: str,
    user_id: str = Depends(verify_account_ownership),
    db: Session = Depends(get_db),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve ranked eligible interventions minimizing expected shortfall cost."""
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

    approval_service = ApprovalService(db)

    # Queue mandatory human approval proposals into database if not already queued
    for prop in exec_result.proposals:
        if prop.mandatory_human_approval:
            approval_service.submit_proposal(prop)

    return exec_result.proposals
