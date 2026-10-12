"""Latency benchmark script profiling FinSight AI components against the 1.5s SLA target."""

from datetime import datetime
import json
from pathlib import Path
import time
from typing import Dict, List
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

from finsight.agentic_core.graph import FinsightAgentGraph
from finsight.config import ARTIFACTS_DIR, PROJECT_ROOT, REPORTS_DIR
from finsight.features.feature_pipeline import compute_point_in_time_features
from finsight.forecasting.deterministic_cashflow import forecast_deterministic_cashflow
from finsight.forecasting.probabilistic_forecaster import forecast_probabilistic_cashflow
from finsight.ingestion.csv_loader import load_transactions_from_csv
from finsight.ml_core.predict import RiskPredictor


def profile_callable(fn, n_runs: int = 25) -> Dict[str, float]:
    """Execute callable n_runs times and compute latency statistics in milliseconds."""
    durations_ms = []
    # Warmup
    fn()

    for _ in range(n_runs):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        durations_ms.append((t1 - t0) * 1000.0)

    arr = np.array(durations_ms)
    return {
        "runs": n_runs,
        "mean_ms": round(float(np.mean(arr)), 2),
        "std_ms": round(float(np.std(arr)), 2),
        "min_ms": round(float(np.min(arr)), 2),
        "p50_ms": round(float(np.percentile(arr, 50)), 2),
        "p95_ms": round(float(np.percentile(arr, 95)), 2),
        "p99_ms": round(float(np.percentile(arr, 99)), 2),
        "max_ms": round(float(np.max(arr)), 2),
    }


def main():
    print("=" * 70)
    print("           FINSIGHT AI — LATENCY BENCHMARK SUITE")
    print("=" * 70)

    tz = ZoneInfo("Asia/Dhaka")
    snapshot_dt = datetime(2024, 3, 1, 12, 0, tzinfo=tz)

    csv_path = PROJECT_ROOT / "data" / "synthetic" / "transactions.csv"
    if not csv_path.exists():
        print(f"Error: {csv_path} not found. Please run scripts/generate_synthetic_data.py first.")
        return

    # Load transactions for testing
    all_txs, _ = load_transactions_from_csv(csv_path)
    stable_txs = [t for t in all_txs if t.account_id == "ACC_001_STABLE"]
    latest_bal = stable_txs[-1].balance_after if stable_txs else 100000.0

    predictor = RiskPredictor()
    graph = FinsightAgentGraph()

    results = {}

    # 1. Ingestion & Validation
    print("\n[1/6] Benchmarking Ingestion & Schema Validation...")
    results["csv_ingestion_and_validation"] = profile_callable(
        lambda: load_transactions_from_csv(csv_path),
        n_runs=15,
    )

    # 2. Point-in-Time Feature Engineering
    print("[2/6] Benchmarking Feature Extraction...")
    results["feature_engineering"] = profile_callable(
        lambda: compute_point_in_time_features(stable_txs, snapshot_dt),
        n_runs=30,
    )
    features = compute_point_in_time_features(stable_txs, snapshot_dt)

    # 3. Deterministic Forecasting
    print("[3/6] Benchmarking Deterministic Cashflow Forecasting...")
    results["deterministic_forecasting"] = profile_callable(
        lambda: forecast_deterministic_cashflow(
            history=stable_txs,
            current_balance=latest_bal,
            snapshot_dt=snapshot_dt,
            account_id="ACC_001_STABLE",
        ),
        n_runs=30,
    )

    # 4. Probabilistic Forecasting
    print("[4/6] Benchmarking Probabilistic Forecasting (100 paths)...")
    results["probabilistic_forecasting"] = profile_callable(
        lambda: forecast_probabilistic_cashflow(
            history=stable_txs,
            current_balance=latest_bal,
            snapshot_dt=snapshot_dt,
            account_id="ACC_001_STABLE",
            n_simulations=100,
        ),
        n_runs=20,
    )

    # 5. Risk Inference & Tree SHAP Explanation
    print("[5/6] Benchmarking Risk Inference + SHAP Explanation...")
    results["risk_inference_and_shap"] = profile_callable(
        lambda: predictor.predict_risk(
            features_dict=features,
            account_id="ACC_001_STABLE",
            timestamp_str=snapshot_dt.isoformat(),
        ),
        n_runs=30,
    )

    # 6. End-to-End Agent Graph Pipeline
    print("[6/6] Benchmarking End-to-End Agent Graph Execution...")
    results["end_to_end_agent_graph"] = profile_callable(
        lambda: graph.run(
            account_id="ACC_001_STABLE",
            transactions=stable_txs,
            snapshot_dt=snapshot_dt,
            current_balance=latest_bal,
            is_sme=False,
        ),
        n_runs=25,
    )

    # Summary table
    print("\n" + "=" * 80)
    print(f"{'Component':<35} | {'p50 (ms)':<10} | {'p95 (ms)':<10} | {'p99 (ms)':<10} | {'Status (<1500ms)':<12}")
    print("-" * 80)

    sla_target_ms = 1500.0
    all_within_sla = True

    for comp, stats in results.items():
        p95 = stats["p95_ms"]
        status = "PASSED" if p95 <= sla_target_ms else "WARNING"
        if comp == "end_to_end_agent_graph" and p95 > sla_target_ms:
            all_within_sla = False
        print(f"{comp:<35} | {stats['p50_ms']:<10.2f} | {p95:<10.2f} | {stats['p99_ms']:<10.2f} | {status:<12}")

    print("=" * 80)
    e2e_p95 = results["end_to_end_agent_graph"]["p95_ms"]
    print(f"\nEnd-to-End Pipeline p95 Latency: {e2e_p95:.2f} ms")
    if e2e_p95 <= sla_target_ms:
        print(f"VERDICT: PASSED SLA target of {sla_target_ms} ms (Headroom: {sla_target_ms - e2e_p95:.1f} ms)")
    else:
        print(f"VERDICT: EXCEEDED SLA target of {sla_target_ms} ms by {e2e_p95 - sla_target_ms:.1f} ms")

    # Save artifact
    out_path = REPORTS_DIR / "latency_benchmark_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    report_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "sla_target_ms": sla_target_ms,
        "all_within_sla": all_within_sla,
        "components": results,
    }
    with open(out_path, "w") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nDetailed latency benchmark report saved to: {out_path}")


if __name__ == "__main__":
    main()
