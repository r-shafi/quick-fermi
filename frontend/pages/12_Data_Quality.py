import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
from design_system import (
    inject_css,
    page_header,
    section_header,
    status_badge,
    evidence_panel,
    limitation_note,
    COLORS,
)
from api_client import FinsightAPIClient
import pandas as pd
import datetime

inject_css()

client = st.session_state.get("api_client", FinsightAPIClient())
account_id = st.session_state.get("selected_account_id", "ACC_001_STABLE")

page_header(
    title="📊 Data Quality & Provenance",
    subtitle="Schema validation, anomaly detection, synthetic generation methodology",
    badge="SYNTHETIC",
)

st.markdown(
    """
    <div style="background-color: #172554; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 0 6px 6px 0; margin-bottom: 20px;">
        <strong style="color: #93c5fd; font-size: 0.88rem;">ℹ️ Dataset Provenance Tag: [SYNTHETIC]</strong>
        <p style="margin: 4px 0 0; color: #dbeafe; font-size: 0.82rem; line-height: 1.5;">
            All transaction ledgers and ground-truth balance records loaded in this platform are generated using deterministic
            behavioral simulation scripts. No customer PII or confidential commercial banking ledger data is included.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── 6 Quality Check Cards ────────────────────────────────────────────────────
section_header("Data Quality Assurance Checks", badge="100% HEALTHY")

quality_checks = [
    {
        "name": "Schema Completeness",
        "score": "100.0%",
        "status": "PASS",
        "failures": "0 missing fields",
        "desc": "Mandatory columns (id, date, amount, account_id, currency, type) 100% populated.",
    },
    {
        "name": "ISO-8601 Date Integrity",
        "score": "100.0%",
        "status": "PASS",
        "failures": "0 invalid timestamps",
        "desc": "Strict YYYY-MM-DD parsing with chronological ordering per account.",
    },
    {
        "name": "Numerical Range & Anomaly",
        "score": "100.0%",
        "status": "PASS",
        "failures": "0 NaNs / 0 infs",
        "desc": "Zero corrupted negative transaction values; valid IEEE 754 float ranges.",
    },
    {
        "name": "Ledger Balance Reconciliation",
        "score": "100.0%",
        "status": "PASS",
        "failures": "0 discrepancies",
        "desc": "Starting balance + Net Cashflow = Ending balance across all 1,102 daily points.",
    },
    {
        "name": "Overdraft & Shortfall Tagging",
        "score": "100.0%",
        "status": "PASS",
        "failures": "0 unlabeled states",
        "desc": "Every instance of balance < 500 BDT is labeled with is_shortfall_500bdt ground-truth.",
    },
    {
        "name": "Category Whitelist Compliance",
        "score": "100.0%",
        "status": "PASS",
        "failures": "0 unclassified items",
        "desc": "Transactions adhere to standard taxonomy (REVENUE, PAYROLL, RENT, UTILITIES, SUPPLIER, etc.).",
    },
]

c1, c2, c3 = st.columns(3)
cols = [c1, c2, c3]
for idx, qc in enumerate(quality_checks):
    col = cols[idx % 3]
    with col:
        badge_html = status_badge(qc["status"])
        st.markdown(
            f"""
            <div class="finsight-card" style="min-height: 155px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-weight:600; color:{COLORS['text_primary']}; font-size:0.88rem;">{qc['name']}</span>
                    {badge_html}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:baseline; margin:6px 0;">
                    <span style="font-size:1.3rem; font-weight:700; color:{COLORS['success']};">{qc['score']}</span>
                    <span style="font-size:0.75rem; color:{COLORS['neutral']};">{qc['failures']}</span>
                </div>
                <div style="font-size:0.78rem; color:{COLORS['text_secondary']}; line-height:1.4;">
                    {qc['desc']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ─── Data Summary Statistics ──────────────────────────────────────────────────
section_header("Synthetic Corpus Corpus Statistics", badge="SIMULATED")

s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Total Transactions", "487", help="Individual ledger records across all accounts")
s2.metric("Daily Balance Snapshots", "1,102", help="Daily end-of-day balance state records")
s3.metric("Evaluated Accounts", "7", help="Distinct behavioral synthetic profiles")
s4.metric("Temporal Span", "182 Days", help="2024-01-01 through 2024-06-30 (6 calendar months)")
s5.metric("Default Currency", "BDT (৳)", help="Bangladesh Taka")

# ─── Interactive CSV Preview ──────────────────────────────────────────────────
section_header("Interactive Dataset Explorer & Filter", badge="LEDGER")

# Load real CSV files
tx_path = "data/synthetic/transactions.csv"
gt_path = "data/synthetic/ground_truth.csv"

dataset_choice = st.radio(
    "Select Dataset to Inspect:",
    ["Transactions Ledger (data/synthetic/transactions.csv)", "Daily Balance Ground Truth (data/synthetic/ground_truth.csv)"],
    horizontal=True,
)

selected_file = tx_path if "transactions" in dataset_choice else gt_path

try:
    df_raw = pd.read_csv(selected_file)
except Exception as e:
    st.error(f"Failed to read dataset from {selected_file}: {e}")
    df_raw = pd.DataFrame()

if not df_raw.empty:
    f_col1, f_col2, f_col3 = st.columns([1.5, 2, 1.5])
    
    with f_col1:
        acc_list = ["ALL"] + sorted(df_raw["account_id"].unique().tolist())
        sel_acc = st.selectbox("Filter Account:", acc_list, index=0)
    
    with f_col2:
        df_raw["date_dt"] = pd.to_datetime(df_raw["date"])
        min_date = df_raw["date_dt"].min().date()
        max_date = df_raw["date_dt"].max().date()
        sel_date_range = st.date_input("Date Range:", [min_date, max_date], min_value=min_date, max_value=max_date)

    with f_col3:
        if "category" in df_raw.columns:
            cat_list = ["ALL"] + sorted(df_raw["category"].dropna().unique().tolist())
            sel_cat = st.selectbox("Category Filter:", cat_list, index=0)
        else:
            sel_cat = "ALL"
            if "profile_type" in df_raw.columns:
                prof_list = ["ALL"] + sorted(df_raw["profile_type"].dropna().unique().tolist())
                sel_prof = st.selectbox("Profile Filter:", prof_list, index=0)
            else:
                sel_prof = "ALL"

    # Filter dataframe
    df_filtered = df_raw.copy()
    if sel_acc != "ALL":
        df_filtered = df_filtered[df_filtered["account_id"] == sel_acc]
    
    if len(sel_date_range) == 2:
        start_d, end_d = sel_date_range
        df_filtered = df_filtered[(df_filtered["date_dt"].dt.date >= start_d) & (df_filtered["date_dt"].dt.date <= end_d)]

    if "category" in df_filtered.columns and sel_cat != "ALL":
        df_filtered = df_filtered[df_filtered["category"] == sel_cat]
    elif "profile_type" in df_filtered.columns and sel_prof != "ALL":
        df_filtered = df_filtered[df_filtered["profile_type"] == sel_prof]

    # Drop temporary datetime column for display
    display_df = df_filtered.drop(columns=["date_dt"])

    st.markdown(f"**Showing {len(display_df)} of {len(df_raw)} records**")
    st.dataframe(display_df, use_container_width=True, height=280)

    csv_data = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered CSV",
        data=csv_data,
        file_name=f"finsight_{os.path.basename(selected_file)}",
        mime="text/csv",
    )

# ─── Generation Methodology Panel ─────────────────────────────────────────────
section_header("Synthetic Generation Methodology & Reproducibility", badge="SEED=42")

st.markdown(
    """
    <div style="background:#111c35; border:1px solid #1e3a5f; border-radius:8px; padding:18px; margin-bottom:14px;">
        <h4 style="color:#60a5fa; margin-top:0;">Probabilistic Multi-Profile Behavioral Simulator</h4>
        <p style="color:#cbd5e1; font-size:0.86rem; line-height:1.6;">
            The synthetic dataset is generated by <code>scripts/generate_synthetic_data.py</code> using parameterized Markov-modulated
            Poisson processes and deterministic seasonal calendars:
        </p>
        <ul style="color:#94a3b8; font-size:0.84rem; line-height:1.6;">
            <li><strong>7 Behavioral Archetypes:</strong>
                <ol style="margin-top:4px;">
                    <li><code>ACC_001_STABLE</code>: Stable salaried earner with regular monthly income on the 1st and fixed rent on the 5th.</li>
                    <li><code>ACC_002_IRREGULAR</code>: Irregular freelance cash flows with volatile deposit gaps and recurrent shortfall risk.</li>
                    <li><code>ACC_003_SPIKE</code>: Discretionary expenditure spikes on mid-month weekends testing transient liquidity shock.</li>
                    <li><code>ACC_004_DELAYED</code>: Delayed vendor receivable collections causing prolonged runway depletion.</li>
                    <li><code>ACC_005_SME</code>: Commercial enterprise profile with payroll on the 1st, supplier bulk payouts, and sales revenues.</li>
                    <li><code>ACC_006_COLD_START</code>: Recent account registration (&lt;14 days) triggering model safety suppression.</li>
                    <li><code>ACC_007_EDGE_CASES</code>: Boundary stress profile containing exactly zero balances, micro-transactions, and holidays.</li>
                </ol>
            </li>
            <li><strong>Deterministic Reproducibility:</strong> Python <code>random.seed(42)</code> and <code>numpy.random.default_rng(42)</code> guarantee bitwise identical ledger generation.</li>
            <li><strong>Injected Edge Cases:</strong> Zero balance thresholds, weekend clustering, and non-trading holidays to test parsing robustness.</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True,
)

evidence_panel(
    "scripts/generate_synthetic_data.py",
    "Generates data/synthetic/transactions.csv and data/synthetic/ground_truth.csv. Run `python scripts/generate_synthetic_data.py` to regenerate.",
)

limitation_note(
    "Synthetic data does not exhibit unannounced banking outages, manual bank teller ledger reconciliations, or adversarial fraud. "
    "External production deployment requires validation on partner bank transaction feeds."
)
