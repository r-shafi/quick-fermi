"""Evaluation reports and benchmark metrics API routes."""

import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from finsight.api.dependencies import enforce_rate_limit, get_current_user
from finsight.rl.offline_evaluation import compare_all_policies

router = APIRouter(prefix="/api/v1/evaluations", tags=["Evaluations"])

from finsight.config import PROJECT_ROOT, REPORTS_DIR

DATA_DIR = PROJECT_ROOT / "data" / "synthetic"


@router.get("/model")
def get_model_evaluations(
    user_id: str = Depends(get_current_user),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve verified evaluation metrics, calibration curves, and cost comparison for candidate models."""
    report_file = REPORTS_DIR / "model_comparison_report.json"
    if not report_file.exists():
        return {
            "status": "NOT_EVALUATED",
            "message": "Model evaluation has not yet been executed.",
            "models": {},
        }

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["dataset_type"] = "SYNTHETIC_SIMULATION"
    data["evaluation_protocol"] = "Temporal Holdout (60% Train, 20% Val, 20% Test)"
    data["disclaimer"] = "These metrics reflect simulated synthetic accounts. No real bank customers were tested."
    return data


@router.get("/policy")
def get_policy_evaluations(
    user_id: str = Depends(get_current_user),
    _rate: None = Depends(enforce_rate_limit),
):
    """Retrieve offline policy evaluation comparing Never Intervene, Fixed Rule, and Cost-Sensitive Supervised."""
    tx_file = DATA_DIR / "transactions.csv"
    gt_file = DATA_DIR / "ground_truth.csv"

    if not tx_file.exists() or not gt_file.exists():
        return {
            "status": "NOT_EVALUATED",
            "message": "Synthetic datasets not found for policy evaluation.",
        }

    from finsight.ml_core.train import build_training_dataset
    df_data = build_training_dataset(tx_file, gt_file)
    results = compare_all_policies(df_data)

    return {
        "status": "COMPLETED",
        "dataset_samples": len(df_data),
        "evaluation_method": "Counterfactual Simulation Environment",
        "policies": results,
        "disclaimer": "Simulated reward improvements do not prove real-world financial benefit.",
    }
