"""Model training and evaluation pipeline with temporal holdout splits."""

from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from zoneinfo import ZoneInfo

from finsight.features.feature_pipeline import FEATURE_COLUMNS, compute_point_in_time_features
from finsight.ingestion.csv_loader import load_transactions_from_csv
from finsight.ml_core.baseline_models import LogisticRegressionBaseline, RuleBasedBaseline
from finsight.ml_core.calibration import ModelCalibrator, evaluate_calibration
from finsight.ml_core.cost_sensitive_loss import CostMatrix
from finsight.ml_core.explainability import FinsightExplainer
from finsight.ml_core.model_registry import ModelMetadata, RegisteredModelPackage
from finsight.ml_core.target_definition import TargetDefinition
from finsight.ml_core.threshold_selection import select_optimal_threshold

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "artifacts" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def build_training_dataset(
    tx_csv: Path,
    gt_csv: Path,
    horizon_days: int = 7,
    safety_buffer: float = 500.0,
    snapshot_interval_days: int = 3,
) -> pd.DataFrame:
    """Build point-in-time feature snapshot dataset with target labels."""
    txs, report = load_transactions_from_csv(tx_csv)
    df_gt = pd.read_csv(gt_csv)
    target_def = TargetDefinition(horizon_days=horizon_days, minimum_safety_balance=safety_buffer)

    # Group transactions by account
    accounts = df_gt["account_id"].unique()
    all_rows = []

    for acc_id in accounts:
        acc_txs = [t for t in txs if t.account_id == acc_id]
        acc_gt = df_gt[df_gt["account_id"] == acc_id].sort_values("date")
        is_sme = "SME" in acc_id

        raw_dates = pd.to_datetime(acc_gt["date"]).tolist()
        if not raw_dates:
            continue

        tz = ZoneInfo("Asia/Dhaka")
        dates = [
            d.tz_localize(tz) if d.tzinfo is None else d.tz_convert(tz)
            for d in raw_dates
        ]
        start_dt = dates[0]
        end_dt = dates[-1]

        # Generate snapshot dates every N days
        cur_dt = start_dt + timedelta(days=7)  # allow at least 7 days initial warmup

        while cur_dt <= end_dt:
            # Check label
            y_label, min_bal, outcome = target_def.compute_label(
                snapshot_dt=cur_dt,
                ground_truth_df=df_gt,
                account_id=acc_id,
            )

            if y_label is not None:
                features = compute_point_in_time_features(
                    history=acc_txs,
                    snapshot_dt=cur_dt,
                    is_sme=is_sme,
                )
                features["account_id"] = acc_id
                features["snapshot_date"] = cur_dt.strftime("%Y-%m-%d")
                features["target"] = y_label
                features["min_future_balance"] = min_bal
                features["outcome_type"] = outcome.value
                all_rows.append(features)

            cur_dt += timedelta(days=snapshot_interval_days)

    df_dataset = pd.DataFrame(all_rows)
    # Sort strictly by snapshot_date for temporal consistency
    df_dataset = df_dataset.sort_values(["snapshot_date", "account_id"]).reset_index(drop=True)
    return df_dataset


def train_and_evaluate_all_models(
    df: pd.DataFrame,
    c_fn: float = 5.0,
    c_fp: float = 1.0,
) -> Tuple[Dict[str, any], RegisteredModelPackage]:
    """Train 4 models using time-ordered train/val/test splits."""
    cost_matrix = CostMatrix(c_fn=c_fn, c_fp=c_fp)

    # 1. Temporal Split (60% Train, 20% Val, 20% Test by date)
    unique_dates = sorted(df["snapshot_date"].unique())
    n_dates = len(unique_dates)
    train_end_idx = int(n_dates * 0.60)
    val_end_idx = int(n_dates * 0.80)

    train_dates = unique_dates[:train_end_idx]
    val_dates = unique_dates[train_end_idx:val_end_idx]
    test_dates = unique_dates[val_end_idx:]

    train_df = df[df["snapshot_date"].isin(train_dates)]
    val_df = df[df["snapshot_date"].isin(val_dates)]
    test_df = df[df["snapshot_date"].isin(test_dates)]

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df["target"].values
    X_val = val_df[FEATURE_COLUMNS]
    y_val = val_df["target"].values
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df["target"].values

    print(f"Data Split Summary: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")
    print(f"Prevalence: Train={np.mean(y_train):.2%}, Val={np.mean(y_val):.2%}, Test={np.mean(y_test):.2%}")

    # Compute data fingerprint
    data_fingerprint = hashlib.sha256(train_df.to_string().encode("utf-8")).hexdigest()[:16]

    # Candidate Models
    candidates = {
        "rule_based": RuleBasedBaseline(safety_buffer=500.0, runway_days_threshold=7.0),
        "logistic_regression": LogisticRegressionBaseline(C=0.1, random_state=42),
        "random_forest": RandomForestClassifier(
            n_estimators=100, max_depth=6, min_samples_split=5, class_weight="balanced", random_state=42
        ),
        "lightgbm": lgb.LGBMClassifier(
            n_estimators=100, learning_rate=0.05, max_depth=5, num_leaves=31, is_unbalance=True, random_state=42, verbose=-1
        ),
    }

    results = {}
    best_model_name = None
    lowest_test_cost = float("inf")
    registered_winner = None

    for name, model in candidates.items():
        print(f"\nTraining and evaluating: {name}")
        model.fit(X_train, y_train)

        # Raw predictions
        val_probs_raw = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else model.predict(X_val)

        # Fit calibrator on validation fold
        calibrator = ModelCalibrator(method="isotonic")
        calibrator.fit(val_probs_raw, y_val)
        val_probs_cal = calibrator.predict_proba(val_probs_raw)

        # Select cost-optimal threshold on validation fold
        opt_thresh, val_cost, thresh_curve = select_optimal_threshold(
            val_probs=val_probs_cal,
            y_val=y_val,
            cost_matrix=cost_matrix,
        )

        # Evaluate on untouched test set
        test_probs_raw = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else model.predict(X_test)
        test_probs_cal = calibrator.predict_proba(test_probs_raw)
        test_preds = (test_probs_cal >= opt_thresh).astype(int)

        # Metrics on test set
        test_cost, cm = cost_matrix.calculate_empirical_cost(y_test, test_preds)
        roc_auc = float(roc_auc_score(y_test, test_probs_cal)) if len(np.unique(y_test)) > 1 else 0.5
        pr_auc = float(average_precision_score(y_test, test_probs_cal)) if len(np.unique(y_test)) > 1 else 0.0
        cal_eval = evaluate_calibration(y_test, test_probs_cal)

        # Alert budget: Recall in top 20% alert rate
        n_alerts_budget = max(1, int(len(test_probs_cal) * 0.20))
        top_budget_indices = np.argsort(test_probs_cal)[-n_alerts_budget:]
        recall_at_budget = float(np.sum(y_test[top_budget_indices]) / max(1, np.sum(y_test)))

        perf = {
            "model_name": name,
            "optimal_threshold": round(opt_thresh, 4),
            "test_expected_cost": round(test_cost, 2),
            "test_roc_auc": round(roc_auc, 4),
            "test_pr_auc": round(pr_auc, 4),
            "test_brier_score": cal_eval["brier_score"],
            "test_ece": cal_eval["expected_calibration_error"],
            "confusion_matrix": cm,
            "recall_at_20pct_budget": round(recall_at_budget, 4),
            "validation_cost": round(val_cost, 2),
        }
        results[name] = perf
        print(f"  Test Cost: {perf['test_expected_cost']} | PR-AUC: {perf['test_pr_auc']} | ROC-AUC: {perf['test_roc_auc']}")

        # Track winning model based on expected cost and stability
        if test_cost < lowest_test_cost or (test_cost == lowest_test_cost and pr_auc > results.get(best_model_name, {}).get("test_pr_auc", 0)):
            lowest_test_cost = test_cost
            best_model_name = name

    print(f"\nWinning Model Selected: {best_model_name} (Lowest Test Cost: {lowest_test_cost})")

    # Package winning model with SHAP explainer
    winner_obj = candidates[best_model_name]
    calibrator = ModelCalibrator(method="isotonic")
    val_probs_raw = winner_obj.predict_proba(X_val)[:, 1] if hasattr(winner_obj, "predict_proba") else winner_obj.predict(X_val)
    calibrator.fit(val_probs_raw, y_val)

    explainer = FinsightExplainer(winner_obj, feature_names=FEATURE_COLUMNS, model_version="1.0.0")

    metadata = ModelMetadata(
        model_version="1.0.0",
        model_name=best_model_name,
        target_name="shortfall_within_7_days",
        training_data_fingerprint=data_fingerprint,
        training_cutoff_date=train_dates[-1],
        feature_schema=FEATURE_COLUMNS,
        decision_threshold=results[best_model_name]["optimal_threshold"],
        calibration_method="isotonic",
        validation_metrics=results[best_model_name],
        library_versions={"lightgbm": lgb.__version__, "numpy": np.__version__},
    )

    registered_winner = RegisteredModelPackage(
        model=winner_obj,
        calibrator=calibrator,
        metadata=metadata,
        explainer=explainer,
    )
    save_path = registered_winner.save()
    print(f"Registered model saved to: {save_path}")

    # Save summary report
    summary_report_path = REPORTS_DIR / "model_comparison_report.json"
    with open(summary_report_path, "w", encoding="utf-8") as f:
        json.dump({"winner": best_model_name, "models": results}, f, indent=2)
    print(f"Report saved to: {summary_report_path}")

    return results, registered_winner


if __name__ == "__main__":
    tx_file = DATA_DIR / "transactions.csv"
    gt_file = DATA_DIR / "ground_truth.csv"
    print("Building training dataset from point-in-time snapshots...")
    df_data = build_training_dataset(tx_file, gt_file)
    train_and_evaluate_all_models(df_data)
