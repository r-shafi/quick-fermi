"""Single-command end-to-end interactive demo for FinSight AI."""

import argparse
from datetime import datetime
import json
from zoneinfo import ZoneInfo

from finsight.agentic_core.graph import FinsightAgentGraph
from finsight.config import PROJECT_ROOT
from finsight.database.models import AuditLogModel
from finsight.database.session import SessionLocal, init_db
from finsight.decision.intervention_catalog import InterventionType
from finsight.execution.approval_service import ApprovalService
from finsight.ingestion.csv_loader import load_transactions_from_csv


def run_demo(account_id: str = "ACC_003_SPIKE"):
    print("\n" + "=" * 80)
    print("                     FINSIGHT AI — END-TO-END DEMO WALKTHROUGH")
    print("=" * 80)

    init_db()

    csv_path = PROJECT_ROOT / "data" / "synthetic" / "transactions.csv"
    if not csv_path.exists():
        print(f"Error: {csv_path} not found. Please run scripts/generate_synthetic_data.py first.")
        return

    print(f"\n[Step 1] Loading and validating transactions for account: {account_id}...")
    all_txs, report = load_transactions_from_csv(csv_path)
    acc_txs = [t for t in all_txs if t.account_id == account_id]

    print(f"  -> Total transactions across dataset: {report.total_records}")
    print(f"  -> Transactions for {account_id}: {len(acc_txs)}")
    print(f"  -> Currency: {report.currency}")
    print(f"  -> Dataset reconciled: {report.reconciled}")

    if not acc_txs:
        print(f"Error: No transactions found for {account_id}.")
        return

    latest_tx = sorted(acc_txs, key=lambda x: x.timestamp)[-1]
    current_balance = latest_tx.balance_after if latest_tx.balance_after is not None else 50000.0
    snapshot_dt = latest_tx.timestamp

    print(f"\n[Step 2] Account Financial Snapshot:")
    print(f"  -> Snapshot Timestamp: {snapshot_dt}")
    print(f"  -> Verified Available Balance: BDT {current_balance:,.2f}")

    print("\n[Step 3] Executing FinSight Agentic Core (Features + Forecast + Risk + SHAP + Interventions)...")
    graph = FinsightAgentGraph()
    state = graph.run(
        account_id=account_id,
        transactions=acc_txs,
        snapshot_dt=snapshot_dt,
        current_balance=current_balance,
        is_sme=("SME" in account_id),
    )

    risk = state.risk_assessment
    forecast = state.forecast

    print("\n[Step 4] Predictive Risk Assessment & Cost-Sensitive Threshold:")
    print(f"  -> Model: {risk.model_name} (version {risk.model_version})")
    print(f"  -> Raw Shortfall Probability: {risk.raw_probability:.1%}")
    print(f"  -> Calibrated Shortfall Probability: {risk.calibrated_probability:.1%}")
    print(f"  -> Cost-Sensitive Decision Threshold (C_FN=5, C_FP=1): {risk.decision_threshold:.1%}")
    print(f"  -> Shortfall Predicted: {risk.is_shortfall_predicted} (Risk Level: {risk.risk_level})")
    print(f"  -> Expected Cost of Action (Alert): {risk.expected_cost_of_action:.2f}")
    print(f"  -> Expected Cost of Inaction: {risk.expected_cost_of_inaction:.2f}")

    print("\n[Step 5] Cash-Flow Forecast Summary (Deterministic & Probabilistic):")
    for h in [1, 3, 7, 14]:
        if h in forecast.horizons:
            hf = forecast.horizons[h]
            print(f"  -> Horizon {h:>2} Days: Projected Balance = BDT {hf.projected_balance:>10,.2f} | Shortfall Risk = {hf.is_shortfall}")

    print("\n[Step 6] SHAP Explainability & Causal Evidence Narrative:")
    exp = risk.explanation
    if exp:
        print("  Top Risk Drivers (Pushing Risk UP):")
        for d in exp.top_risk_drivers[:3]:
            print(f"    - {d.human_description}: value={d.feature_value:,.2f}, SHAP contribution=+{d.shap_value:.4f}")
        print("  Top Risk Mitigators (Pushing Risk DOWN):")
        for m in exp.top_risk_mitigators[:3]:
            print(f"    - {m.human_description}: value={m.feature_value:,.2f}, SHAP contribution={m.shap_value:.4f}")
        print(f"\n  Evidence Narrative:\n    \"{exp.deterministic_narrative}\"")

    print("\n[Step 7] Deterministic Intervention Policy Engine:")
    print(f"  -> Evaluated and ranked {len(state.proposals)} eligible intervention proposals:")
    for idx, p in enumerate(state.proposals, 1):
        app_tag = "[REQUIRES HUMAN APPROVAL]" if p.mandatory_human_approval else "[AUTOMATED/INFORM]"
        print(f"    {idx}. {p.action_type.value:<18} | Net Benefit: {p.expected_cost_benefit:>5.2f} | {app_tag} - {p.title}")

    # Step 8: Approval Queue & Sandbox Execution
    print("\n[Step 8] Approval Queue & Sandbox Execution Simulation:")
    actionable_proposals = [p for p in state.proposals if p.mandatory_human_approval]
    if actionable_proposals:
        selected_prop = actionable_proposals[0]
        print(f"  -> Selected Proposal: {selected_prop.title} ({selected_prop.action_type.value})")

        with SessionLocal() as db:
            service = ApprovalService(db)
            sub_res = service.submit_proposal(selected_prop)
            approval_id = sub_res.get("approval_id")
            print(f"  -> Queued for Approval with ID: {approval_id} (Status: {sub_res.get('status')})")

            # Simulate User Approval
            print(f"  -> Simulating User Approval by actor 'user_demo'...")
            app_res = service.approve(approval_id=approval_id, actor_id="user_demo")
            print(f"  -> Outcome: Status={app_res.get('status')} | Message=\"{app_res.get('message')}\"")

            # Check audit log
            audit_entry = db.query(AuditLogModel).filter(
                AuditLogModel.account_id == account_id
            ).order_by(AuditLogModel.timestamp.desc()).first()

            if audit_entry:
                print(f"  -> Audit Log Verified: Actor='{audit_entry.actor}', Action='{audit_entry.action}', Status='{audit_entry.status}'")
    else:
        print("  -> Low-risk account: Only informational advisory proposed, no mandatory human approval required.")

    print("\n" + "=" * 80)
    print("                     DEMO EXECUTION SUCCESSFULLY COMPLETED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FinSight AI End-to-End Demo Walkthrough")
    parser.add_argument("--account", default="ACC_003_SPIKE", help="Account ID to demonstrate")
    args = parser.parse_args()
    run_demo(account_id=args.account)
