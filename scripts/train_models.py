"""Command-line script to train candidate models and select the best version."""

import argparse
from pathlib import Path
from finsight.ml_core.train import build_training_dataset, train_and_evaluate_all_models

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"


def main():
    parser = argparse.ArgumentParser(description="Train candidate shortfall risk models.")
    parser.add_argument("--tx_file", type=str, default=str(DATA_DIR / "transactions.csv"))
    parser.add_argument("--gt_file", type=str, default=str(DATA_DIR / "ground_truth.csv"))
    parser.add_argument("--cfn", type=float, default=5.0, help="Cost of False Negative")
    parser.add_argument("--cfp", type=float, default=1.0, help="Cost of False Positive")
    args = parser.parse_args()

    print("Step 1: Building point-in-time training snapshots...")
    df_data = build_training_dataset(Path(args.tx_file), Path(args.gt_file))
    print(f"Dataset generated with {len(df_data)} snapshot rows across accounts.")

    print("\nStep 2: Training and comparing all 4 candidate models...")
    results, winner = train_and_evaluate_all_models(df_data, c_fn=args.cfn, c_fp=args.cfp)

    print("\nTraining completed successfully.")


if __name__ == "__main__":
    main()
