"""Synthetic financial data generator producing 7 distinct account profiles.

Includes ground-truth daily balance simulations for objective evaluation.
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import random
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_account_data(
    account_id: str,
    account_type: str,
    start_date: datetime,
    end_date: datetime,
    profile_type: str,
    currency: str = "BDT",
    tz: str = "Asia/Dhaka",
    seed: int = 42,
) -> Tuple[List[Dict], List[Dict]]:
    """Generate transactions and ground truth daily balance trajectory for an account.
    
    Returns:
        (transactions_list, ground_truth_trajectory)
    """
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    transactions = []
    ground_truth = []

    # Initial balance by profile
    if profile_type == "stable_salary":
        balance = 45000.0
        salary_amount = 75000.0
        rent_amount = 22000.0
        utility_amount = 3500.0
    elif profile_type == "irregular_income":
        balance = 25000.0
    elif profile_type == "spending_spike":
        balance = 30000.0
        salary_amount = 50000.0
    elif profile_type == "delayed_salary":
        balance = 15000.0
        salary_amount = 60000.0
    elif profile_type == "sme_cashflow":
        balance = 350000.0
    elif profile_type == "cold_start":
        balance = 12000.0
        # Only 7 days of history
        start_date = end_date - timedelta(days=7)
    elif profile_type == "edge_cases":
        balance = 20000.0
    else:
        balance = 30000.0

    current_date = start_date
    tx_counter = 1

    while current_date <= end_date:
        day_of_month = current_date.day
        day_of_week = current_date.weekday()
        daily_starting_balance = balance

        # --- PROFILE 1: STABLE MONTHLY SALARY ---
        if profile_type == "stable_salary":
            # Salary on 1st of month
            if day_of_month == 1:
                amt = salary_amount
                balance += amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=9, minute=0).isoformat(),
                    "amount": amt,
                    "currency": currency,
                    "transaction_type": "INCOME",
                    "category": "SALARY",
                    "description": "Monthly Salary Corporate Deposit",
                    "counterparty": "Apex Tech Ltd",
                    "is_internal_transfer": False,
                    "is_recurring": True,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Rent on 5th
            if day_of_month == 5:
                amt = rent_amount
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=11, minute=0).isoformat(),
                    "amount": amt,
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "RENT",
                    "description": "Monthly Apartment Rent",
                    "counterparty": "Green Real Estate",
                    "is_internal_transfer": False,
                    "is_recurring": True,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Utilities on 10th
            if day_of_month == 10:
                amt = utility_amount + rng.uniform(-200, 300)
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=14, minute=0).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "UTILITIES",
                    "description": "Electricity & Water Bill",
                    "counterparty": "DESCO Electric",
                    "is_internal_transfer": False,
                    "is_recurring": True,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Groceries 2-3 times a week
            if day_of_week in [1, 4, 6]:
                amt = rng.uniform(800, 2200)
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=18, minute=rng.randint(0, 59)).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "GROCERIES",
                    "description": "Supermarket Groceries",
                    "counterparty": "Shwapno Superstore",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Discretionary dining
            if rng.random() < 0.25:
                amt = rng.uniform(300, 1500)
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=20, minute=rng.randint(0, 59)).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "DINING",
                    "description": "Restaurant Dining",
                    "counterparty": "Cafe Bistro",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

        # --- PROFILE 2: IRREGULAR FREELANCE INCOME ---
        elif profile_type == "irregular_income":
            # Variable freelance invoices (random days, 2-4 times a month)
            if rng.random() < 0.08:
                amt = rng.uniform(15000, 45000)
                balance += amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=15, minute=0).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "INCOME",
                    "category": "INVOICE_RECEIPT",
                    "description": "Client Freelance Contract Payout",
                    "counterparty": "Upwork / Global Client",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Essential rent on 7th
            if day_of_month == 7:
                amt = 16000.0
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=11, minute=0).isoformat(),
                    "amount": amt,
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "RENT",
                    "description": "Studio Flat Rent",
                    "counterparty": "Landlord",
                    "is_internal_transfer": False,
                    "is_recurring": True,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Volatile discretionary spending
            if rng.random() < 0.40:
                amt = rng.uniform(500, 4000)
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=19, minute=rng.randint(0, 59)).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": rng.choice(["ENTERTAINMENT", "SHOPPING", "DINING"]),
                    "description": "Discretionary Lifestyle Spend",
                    "counterparty": "Retail Merchant",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

        # --- PROFILE 3: SUDDEN SPENDING SPIKE (SHORTFALL INDUCED) ---
        elif profile_type == "spending_spike":
            if day_of_month == 1:
                balance += salary_amount
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=9, minute=0).isoformat(),
                    "amount": salary_amount,
                    "currency": currency,
                    "transaction_type": "INCOME",
                    "category": "SALARY",
                    "description": "Monthly Salary",
                    "counterparty": "Delta Corp",
                    "is_internal_transfer": False,
                    "is_recurring": True,
                    "balance_after": balance,
                })
                tx_counter += 1

            if day_of_month == 4:
                balance -= 18000.0
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=10, minute=0).isoformat(),
                    "amount": 18000.0,
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "RENT",
                    "description": "Apartment Rent",
                    "counterparty": "Landlord",
                    "is_internal_transfer": False,
                    "is_recurring": True,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Massive uncharacteristic shopping spike in the middle of month
            if current_date.month in [2, 5, 8] and day_of_month in [16, 17]:
                amt = rng.uniform(25000, 35000)
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=16, minute=0).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "SHOPPING",
                    "description": "Luxury Electronics Purchase",
                    "counterparty": "Gadget Hub Ltd",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Standard living expenses
            if rng.random() < 0.35:
                amt = rng.uniform(600, 1800)
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=19, minute=0).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "GROCERIES",
                    "description": "Daily Living Spend",
                    "counterparty": "Local Mart",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

        # --- PROFILE 4: DELAYED SALARY (CASH SHORTFALL EVENT) ---
        elif profile_type == "delayed_salary":
            # Rent is strictly due on 3rd of month (20,000)
            if day_of_month == 3:
                balance -= 20000.0
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=10, minute=0).isoformat(),
                    "amount": 20000.0,
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "RENT",
                    "description": "House Rent",
                    "counterparty": "Landlord Agency",
                    "is_internal_transfer": False,
                    "is_recurring": True,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Salary is usually on 1st, but delayed to 14th in odd months!
            salary_day = 14 if current_date.month % 2 != 0 else 1
            if day_of_month == salary_day:
                balance += salary_amount
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=11, minute=0).isoformat(),
                    "amount": salary_amount,
                    "currency": currency,
                    "transaction_type": "INCOME",
                    "category": "SALARY",
                    "description": "Monthly Salary (Delayed in odd months)",
                    "counterparty": "Consultancy Partners",
                    "is_internal_transfer": False,
                    "is_recurring": True,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Regular living
            if rng.random() < 0.30:
                amt = rng.uniform(700, 2000)
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=18, minute=0).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "GROCERIES",
                    "description": "Groceries",
                    "counterparty": "Bazaar",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

        # --- PROFILE 5: SME CASH-FLOW MODE ---
        elif profile_type == "sme_cashflow":
            # Client invoice payments (lumpy, 100k - 300k, 1-3 times a month)
            if rng.random() < 0.08:
                amt = rng.uniform(120000, 350000)
                balance += amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=14, minute=0).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "INCOME",
                    "category": "INVOICE_RECEIPT",
                    "description": "B2B Client Invoice Settlement",
                    "counterparty": "Client Enterprises Ltd",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Payroll on 28th (180,000)
            if day_of_month == 28:
                balance -= 180000.0
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=10, minute=0).isoformat(),
                    "amount": 180000.0,
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "PAYROLL",
                    "description": "Monthly Staff Payroll",
                    "counterparty": "Payroll Account",
                    "is_internal_transfer": False,
                    "is_recurring": True,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Commercial Office Rent on 1st (65,000)
            if day_of_month == 1:
                balance -= 65000.0
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=11, minute=0).isoformat(),
                    "amount": 65000.0,
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "RENT",
                    "description": "Commercial Office Lease",
                    "counterparty": "Gulshan Tower Management",
                    "is_internal_transfer": False,
                    "is_recurring": True,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Supplier disbursements (every 4-7 days)
            if day_of_week in [0, 3] and rng.random() < 0.6:
                amt = rng.uniform(30000, 95000)
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=15, minute=0).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "SUPPLIER",
                    "description": "Raw Material Supplier Payment",
                    "counterparty": "Industrial Supplies Corp",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

        # --- PROFILE 6: COLD-START NEW ACCOUNT ---
        elif profile_type == "cold_start":
            # Very short transaction history (few events)
            if day_of_month % 3 == 0:
                amt = rng.uniform(800, 2500)
                balance -= amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=12, minute=0).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "GROCERIES",
                    "description": "Recent Grocery Spend",
                    "counterparty": "Local Store",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

        # --- PROFILE 7: EDGE CASES (REFUNDS, REVERSALS, INTERNAL TRANSFERS, DUPLICATES) ---
        elif profile_type == "edge_cases":
            # Normal expense
            if day_of_week in [1, 3]:
                amt = rng.uniform(500, 1500)
                balance -= amt
                tx_id = f"TX_{account_id}_{tx_counter:05d}"
                transactions.append({
                    "transaction_id": tx_id,
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=12, minute=0).isoformat(),
                    "amount": round(amt, 2),
                    "currency": currency,
                    "transaction_type": "EXPENSE",
                    "category": "DINING",
                    "description": "Cafe Lunch",
                    "counterparty": "Coffee Shop",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

                # Deliberate duplicate record injected
                if rng.random() < 0.2:
                    transactions.append({
                        "transaction_id": tx_id,  # identical ID
                        "account_id": account_id,
                        "timestamp": current_date.replace(hour=12, minute=0).isoformat(),
                        "amount": round(amt, 2),
                        "currency": currency,
                        "transaction_type": "EXPENSE",
                        "category": "DINING",
                        "description": "Cafe Lunch",
                        "counterparty": "Coffee Shop",
                        "is_internal_transfer": False,
                        "is_recurring": False,
                        "balance_after": balance,
                    })

            # Internal transfer
            if day_of_month == 15:
                amt = 5000.0
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=10, minute=0).isoformat(),
                    "amount": amt,
                    "currency": currency,
                    "transaction_type": "TRANSFER",
                    "category": "INTERNAL_TRANSFER",
                    "description": "Internal transfer to savings account",
                    "counterparty": "Self Savings Account",
                    "is_internal_transfer": True,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

            # Refund
            if day_of_month == 20:
                amt = 1200.0
                balance += amt
                transactions.append({
                    "transaction_id": f"TX_{account_id}_{tx_counter:05d}",
                    "account_id": account_id,
                    "timestamp": current_date.replace(hour=16, minute=0).isoformat(),
                    "amount": amt,
                    "currency": currency,
                    "transaction_type": "REFUND",
                    "category": "SHOPPING",
                    "description": "Merchant Purchase Refund",
                    "counterparty": "E-Commerce Return",
                    "is_internal_transfer": False,
                    "is_recurring": False,
                    "balance_after": balance,
                })
                tx_counter += 1

        # Record daily ground truth state
        ground_truth.append({
            "account_id": account_id,
            "date": current_date.strftime("%Y-%m-%d"),
            "profile_type": profile_type,
            "account_type": account_type,
            "currency": currency,
            "starting_balance": round(daily_starting_balance, 2),
            "ending_balance": round(balance, 2),
            "daily_net_change": round(balance - daily_starting_balance, 2),
            "is_shortfall_500bdt": balance < 500.0,
            "is_shortfall_0bdt": balance < 0.0,
        })

        current_date += timedelta(days=1)

    return transactions, ground_truth


def generate_all_synthetic_data(seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generate complete synthetic dataset covering all 7 profiles."""
    tz = "Asia/Dhaka"
    start_date = datetime(2024, 1, 1, tzinfo=ZoneInfo(tz))
    end_date = datetime(2024, 6, 30, tzinfo=ZoneInfo(tz))

    profiles = [
        ("ACC_001_STABLE", "PERSONAL", "stable_salary"),
        ("ACC_002_IRREGULAR", "PERSONAL", "irregular_income"),
        ("ACC_003_SPIKE", "PERSONAL", "spending_spike"),
        ("ACC_004_DELAYED", "PERSONAL", "delayed_salary"),
        ("ACC_005_SME", "SME", "sme_cashflow"),
        ("ACC_006_COLD_START", "PERSONAL", "cold_start"),
        ("ACC_007_EDGE_CASES", "PERSONAL", "edge_cases"),
    ]

    all_txs = []
    all_gt = []

    for acc_id, acc_type, p_type in profiles:
        acc_seed = seed + hash(acc_id) % 1000
        txs, gt = generate_account_data(
            account_id=acc_id,
            account_type=acc_type,
            start_date=start_date,
            end_date=end_date,
            profile_type=p_type,
            currency="BDT",
            tz=tz,
            seed=acc_seed,
        )
        all_txs.extend(txs)
        all_gt.extend(gt)

    df_txs = pd.DataFrame(all_txs)
    df_gt = pd.DataFrame(all_gt)

    # Sort transactions chronologically
    df_txs["timestamp"] = pd.to_datetime(df_txs["timestamp"])
    df_txs = df_txs.sort_values(by=["timestamp", "account_id"]).reset_index(drop=True)

    tx_path = OUTPUT_DIR / "transactions.csv"
    gt_path = OUTPUT_DIR / "ground_truth.csv"

    df_txs.to_csv(tx_path, index=False)
    df_gt.to_csv(gt_path, index=False)

    print(f"Generated {len(df_txs)} transactions saved to {tx_path}")
    print(f"Generated {len(df_gt)} daily ground-truth records saved to {gt_path}")

    return df_txs, df_gt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic financial transaction data.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args()
    generate_all_synthetic_data(seed=args.seed)
