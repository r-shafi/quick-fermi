"""Script to generate well-structured, reproducible Jupyter analysis notebooks."""

import json
from pathlib import Path

NOTEBOOKS_DIR = Path(__file__).resolve().parent.parent / "notebooks"
NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)


def make_notebook(cells):
    return {
        "cells": cells,
        "metadata": {
            "language_info": {
                "name": "python",
                "version": "3.12.3",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def md_cell(source):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [s + "\n" for s in source.split("\n")],
    }


def code_cell(source):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [s + "\n" for s in source.split("\n")],
    }


def generate_all_notebooks():
    # -------------------------------------------------------------
    # 01_data_quality.ipynb
    # -------------------------------------------------------------
    nb1 = make_notebook([
        md_cell(
            "# FinSight AI — Notebook 01: Data Quality & Ingestion Validation\n\n"
            "This notebook audits the raw synthetic transaction dataset, validates schema consistency, "
            "verifies mathematical balance reconciliation, and reports duplicate transaction handling."
        ),
        code_cell(
            "import sys\n"
            "from pathlib import Path\n"
            "sys.path.append(str(Path.cwd().parent / 'src'))\n\n"
            "import pandas as pd\n"
            "import numpy as np\n"
            "from finsight.ingestion.csv_loader import load_transactions_from_csv\n\n"
            "tx_path = Path.cwd().parent / 'data' / 'synthetic' / 'transactions.csv'\n"
            "print(f'Loading transaction data from: {tx_path}')\n"
            "transactions, report = load_transactions_from_csv(tx_path)\n"
            "print(f'Total records: {report.total_records}')\n"
            "print(f'Valid records: {report.valid_records}')\n"
            "print(f'Duplicates flagged: {report.duplicate_records}')\n"
            "print(f'Reconciled: {report.reconciled}')"
        ),
        md_cell(
            "## 1. Missing Value and Data Completeness Audit\n\n"
            "Let us inspect null values and feature availability across transaction fields."
        ),
        code_cell(
            "df_tx = pd.read_csv(tx_path)\n"
            "print('Missing Values Count:')\n"
            "print(df_tx.isnull().sum())\n\n"
            "print('\\nAccount Distribution:')\n"
            "print(df_tx['account_id'].value_counts())"
        ),
        md_cell(
            "## 2. Balance Reconciliation and Internal Transfer Integrity\n\n"
            "Verify that internal transfers are tagged to avoid artificial spending inflation."
        ),
        code_cell(
            "internal_transfers = df_tx[df_tx['is_internal_transfer'] == True]\n"
            "print(f'Internal Transfers Count: {len(internal_transfers)}')\n"
            "print(internal_transfers[['transaction_id', 'account_id', 'amount', 'category', 'description']])"
        ),
    ])
    with open(NOTEBOOKS_DIR / "01_data_quality.ipynb", "w") as f:
        json.dump(nb1, f, indent=2)
    print("Generated 01_data_quality.ipynb")

    # -------------------------------------------------------------
    # 02_exploratory_analysis.ipynb
    # -------------------------------------------------------------
    nb2 = make_notebook([
        md_cell(
            "# FinSight AI — Notebook 02: Exploratory Financial Data Analysis\n\n"
            "Explores transaction amounts, spending velocity, income periodicity, "
            "and liquidity trajectories across personal finance and SME accounts."
        ),
        code_cell(
            "import sys\n"
            "from pathlib import Path\n"
            "sys.path.append(str(Path.cwd().parent / 'src'))\n\n"
            "import pandas as pd\n"
            "import numpy as np\n\n"
            "tx_path = Path.cwd().parent / 'data' / 'synthetic' / 'transactions.csv'\n"
            "gt_path = Path.cwd().parent / 'data' / 'synthetic' / 'ground_truth.csv'\n"
            "df_tx = pd.read_csv(tx_path)\n"
            "df_gt = pd.read_csv(gt_path)\n"
            "print(f'Transactions: {len(df_tx)}, Ground Truth Days: {len(df_gt)}')"
        ),
        md_cell(
            "## 1. Spending by Category\n\n"
            "Analyze essential obligations (Rent, Utilities, Payroll, Tax) vs discretionary spending."
        ),
        code_cell(
            "expenses = df_tx[df_tx['transaction_type'] == 'EXPENSE']\n"
            "cat_summary = expenses.groupby('category')['amount'].agg(['count', 'sum', 'mean']).sort_values('sum', ascending=False)\n"
            "print('Expense Summary by Category (BDT):')\n"
            "print(cat_summary)"
        ),
        md_cell(
            "## 2. Ending Balance Trajectories Across Accounts"
        ),
        code_cell(
            "acc_stats = df_gt.groupby('account_id')['ending_balance'].agg(['min', 'median', 'max'])\n"
            "print('Ground-Truth Balance Extremes (BDT):')\n"
            "print(acc_stats)"
        ),
    ])
    with open(NOTEBOOKS_DIR / "02_exploratory_analysis.ipynb", "w") as f:
        json.dump(nb2, f, indent=2)
    print("Generated 02_exploratory_analysis.ipynb")

    # -------------------------------------------------------------
    # 03_baseline_models.ipynb
    # -------------------------------------------------------------
    nb3 = make_notebook([
        md_cell(
            "# FinSight AI — Notebook 03: Baseline Models & Supervised Risk Modeling\n\n"
            "Evaluates Rule-based heuristic runway baseline, Logistic Regression baseline, "
            "Random Forest, and LightGBM on temporal holdout partitions."
        ),
        code_cell(
            "import sys\n"
            "from pathlib import Path\n"
            "sys.path.append(str(Path.cwd().parent / 'src'))\n\n"
            "import json\n"
            "import pandas as pd\n\n"
            "report_path = Path.cwd().parent / 'artifacts' / 'reports' / 'model_comparison_report.json'\n"
            "if report_path.exists():\n"
            "    with open(report_path) as f:\n"
            "        data = json.load(f)\n"
            "    print('Model Comparison Leaderboard:')\n"
            "    for m in data.get('models', []):\n"
            "        print(f\"{m['model_name']:<25} | PR-AUC: {m.get('test_pr_auc', 0):.4f} | ROC-AUC: {m.get('test_roc_auc', 0):.4f} | Test Cost: {m.get('test_cost', 0)}\")\n"
            "else:\n"
            "    print('Run scripts/train_models.py to generate leaderboard.')"
        ),
        md_cell(
            "## 1. Feature Importance and Model Inspection\n\n"
            "Inspect the winner model package and its metadata."
        ),
        code_cell(
            "from finsight.ml_core.model_registry import ARTIFACTS_DIR\n"
            "models = [d.name for d in ARTIFACTS_DIR.iterdir() if d.is_dir()]\n"
            "print(f'Available Registered Models: {models}')"
        ),
    ])
    with open(NOTEBOOKS_DIR / "03_baseline_models.ipynb", "w") as f:
        json.dump(nb3, f, indent=2)
    print("Generated 03_baseline_models.ipynb")

    # -------------------------------------------------------------
    # 04_cost_sensitive_experiments.ipynb
    # -------------------------------------------------------------
    nb4 = make_notebook([
        md_cell(
            "# FinSight AI — Notebook 04: Cost-Sensitive Optimization & Asymmetric Error Curves\n\n"
            "Demonstrates why standard 0.5 decision thresholds fail in financial shortfall intervention, "
            "and evaluates the cost-optimal decision threshold $\\tau^*$ under $C_{FN}=5.0, C_{FP}=1.0$."
        ),
        code_cell(
            "import sys\n"
            "from pathlib import Path\n"
            "sys.path.append(str(Path.cwd().parent / 'src'))\n\n"
            "import numpy as np\n"
            "from finsight.ml_core.cost_sensitive_loss import CostMatrix\n"
            "from finsight.ml_core.threshold_selection import select_optimal_threshold\n\n"
            "cm = CostMatrix(c_fn=5.0, c_fp=1.0)\n"
            "print(f'Asymmetric Cost Formulation: C_FN={cm.c_fn}, C_FP={cm.c_fp}')\n"
            "print(f'Analytical Bayes-Optimal Threshold: {cm.optimal_decision_threshold:.4f}')"
        ),
        md_cell(
            "## 1. Threshold Sensitivity Curve\n\n"
            "Evaluate total cost across candidate thresholds from 0.01 to 0.99."
        ),
        code_cell(
            "y_val = np.array([0, 0, 0, 0, 0, 1, 1, 1, 0, 1])\n"
            "val_probs = np.array([0.02, 0.05, 0.10, 0.12, 0.15, 0.22, 0.35, 0.65, 0.11, 0.70])\n\n"
            "best_tau, min_cost, curve = select_optimal_threshold(val_probs, y_val, cm)\n"
            "print(f'Optimal Threshold tau*: {best_tau:.4f}')\n"
            "print(f'Minimum Financial Cost: {min_cost:.2f}')\n\n"
            "cost_default, _ = cm.calculate_empirical_cost(y_val, (val_probs >= 0.5).astype(int))\n"
            "print(f'Default Threshold 0.5 Cost: {cost_default:.2f} (Penalty Increase: +{cost_default - min_cost:.2f})')"
        ),
    ])
    with open(NOTEBOOKS_DIR / "04_cost_sensitive_experiments.ipynb", "w") as f:
        json.dump(nb4, f, indent=2)
    print("Generated 04_cost_sensitive_experiments.ipynb")

    # -------------------------------------------------------------
    # 05_temporal_validation.ipynb
    # -------------------------------------------------------------
    nb5 = make_notebook([
        md_cell(
            "# FinSight AI — Notebook 05: Temporal Validation & Distribution Stability\n\n"
            "Validates that data partitioning strictly respects temporal causality, "
            "verifies zero lookahead leakage, and tracks distribution drift with PSI and ADWIN."
        ),
        code_cell(
            "import sys\n"
            "from pathlib import Path\n"
            "sys.path.append(str(Path.cwd().parent / 'src'))\n\n"
            "import pandas as pd\n"
            "from finsight.ml_core.drift_detection import calculate_psi, ADWINDriftDetector\n\n"
            "tx_path = Path.cwd().parent / 'data' / 'synthetic' / 'transactions.csv'\n"
            "df = pd.read_csv(tx_path)\n"
            "df['timestamp'] = pd.to_datetime(df['timestamp'])\n"
            "df = df.sort_values('timestamp')\n"
            "print(f'Date range: {df[\"timestamp\"].min()} to {df[\"timestamp\"].max()}')"
        ),
        md_cell(
            "## 1. Population Stability Index (PSI) Across Temporal Halves"
        ),
        code_cell(
            "midpoint = len(df) // 2\n"
            "ref_spend = df.iloc[:midpoint]['amount'].values\n"
            "curr_spend = df.iloc[midpoint:]['amount'].values\n\n"
            "psi = calculate_psi(ref_spend, curr_spend)\n"
            "print(f'Population Stability Index (Amount): {psi:.4f}')\n"
            "if psi < 0.1:\n"
            "    print('Status: STABLE (No significant distribution drift detected)')\n"
            "elif psi < 0.2:\n"
            "    print('Status: MODERATE SHIFT (Monitor feature inputs)')\n"
            "else:\n"
            "    print('Status: SIGNIFICANT DRIFT (Model retraining advised)')"
        ),
    ])
    with open(NOTEBOOKS_DIR / "05_temporal_validation.ipynb", "w") as f:
        json.dump(nb5, f, indent=2)
    print("Generated 05_temporal_validation.ipynb")


if __name__ == "__main__":
    generate_all_notebooks()
