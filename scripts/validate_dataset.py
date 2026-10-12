"""Dataset validation script producing comprehensive data quality audits."""

import argparse
from pathlib import Path
import pandas as pd
from finsight.ingestion.csv_loader import load_transactions_from_csv

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"


def validate_dataset(csv_path: Path, expected_currency: str = "BDT"):
    print(f"=== Validating Dataset: {csv_path} ===")
    if not csv_path.exists():
        print(f"Error: File does not exist at {csv_path}")
        return False

    df_raw = pd.read_csv(csv_path)
    print(f"Total raw records in CSV: {len(df_raw)}")
    accounts = df_raw["account_id"].unique()
    print(f"Found {len(accounts)} distinct accounts: {list(accounts)}")

    all_passed = True

    for acc_id in accounts:
        acc_df = df_raw[df_raw["account_id"] == acc_id]
        # Test loading via csv_loader
        txs, report = load_transactions_from_csv(
            acc_df,
            expected_currency=expected_currency,
        )

        print(f"\n--- Account: {acc_id} ---")
        print(f"  Valid records: {report.valid_records}/{report.total_records}")
        print(f"  Duplicates detected: {report.duplicate_records}")
        print(f"  Rejected records: {report.rejected_records}")
        print(f"  History span: {report.history_days:.1f} days")
        print(f"  Completeness score: {report.data_completeness_score:.2%}")
        print(f"  Issues reported: {len(report.issues)}")

        for issue in report.issues[:5]:  # print first 5 issues
            print(f"    [{issue.level}] {issue.issue_type}: {issue.message}")
        if len(report.issues) > 5:
            print(f"    ... and {len(report.issues) - 5} more issues.")

        if report.valid_records == 0:
            all_passed = False

    print("\n=== Validation Complete ===")
    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate financial transaction dataset.")
    parser.add_argument(
        "--file",
        type=str,
        default=str(DATA_DIR / "transactions.csv"),
        help="Path to CSV file to validate",
    )
    parser.add_argument("--currency", type=str, default="BDT", help="Expected currency")
    args = parser.parse_args()

    validate_dataset(Path(args.file), expected_currency=args.currency)
