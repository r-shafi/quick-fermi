"""FinSight AI - Multi-page Streamlit Dashboard."""

import streamlit as st
from api_client import FinsightAPIClient

st.set_page_config(
    page_title="FinSight AI — Financial Intervention Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize API Client in session state
if "api_client" not in st.session_state:
    st.session_state.api_client = FinsightAPIClient()

client: FinsightAPIClient = st.session_state.api_client

# Sidebar
st.sidebar.image("https://img.icons8.com/fluency/96/shield.png", width=64)
st.sidebar.title("FinSight AI")
st.sidebar.caption("Cost-Sensitive Financial Intervention Agent")

# Fetch accounts
try:
    accounts = client.list_accounts()
    account_ids = [a["account_id"] for a in accounts]
except Exception as e:
    st.sidebar.error(f"Cannot connect to backend API: {e}")
    account_ids = ["ACC_001_STABLE"]

# Active account selector
selected_acc = st.sidebar.selectbox(
    "Active Account",
    account_ids,
    index=0 if account_ids else 0,
)
st.session_state.selected_account_id = selected_acc

# Account mode badge
is_sme = "SME" in selected_acc
st.sidebar.markdown(f"**Mode:** `{'SME Cash-Flow' if is_sme else 'Personal Finance'}`")
st.sidebar.markdown("**Base Currency:** `BDT (৳)`")

# Upload new CSV in sidebar
with st.sidebar.expander("Upload Transaction CSV"):
    uploaded_file = st.file_uploader("Upload bank/ledger CSV", type=["csv"])
    if uploaded_file is not None:
        if st.button("Process & Validate CSV"):
            with st.spinner("Ingesting and validating..."):
                try:
                    rep = client.upload_csv(
                        file_bytes=uploaded_file.getvalue(),
                        filename=uploaded_file.name,
                        currency="BDT",
                        account_type="SME" if is_sme else "PERSONAL",
                    )
                    st.success(f"Ingested {rep.get('valid_records')} valid records! Duplicates: {rep.get('duplicate_records')}")
                    st.rerun()
                except Exception as err:
                    st.error(f"Upload failed: {err}")

st.sidebar.markdown("---")
st.sidebar.caption("Prototype Version: 0.1.0 | Environment: Sandbox")

# Main Header
st.title("🛡️ FinSight AI: Predictive Financial Intervention Agent")
st.markdown(
    "Anticipate liquidity shortfalls, evaluate cost-asymmetric decisions ($C_{FN}=5.0, C_{FP}=1.0$), "
    "and safeguard financial health with explainable AI and human-in-the-loop approvals."
)

# Quick summary bar
if selected_acc:
    try:
        summary = client.get_account_summary(selected_acc)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Available Balance",
            f"BDT {summary['available_balance']:,.2f}",
            help="Current verified available cash balance",
        )
        c2.metric(
            "Observed History",
            f"{summary['history_days']:.0f} days",
            help="Total days of transaction history",
        )
        c3.metric(
            "Data Freshness",
            f"{summary['data_staleness_days']:.1f} days ago" if summary['data_staleness_days'] < 30 else "Recent",
            help="Days since most recent transaction timestamp",
        )
        c4.metric(
            "Cold Start Status",
            "INSUFFICIENT_HISTORY" if summary["is_cold_start"] else "MATURE",
            delta_color="off",
        )
    except Exception as e:
        st.warning(f"Could not load summary for {selected_acc}: {e}")

st.info("👈 Select a module in the sidebar navigation to view **Overview**, **Cashflow Forecast**, **Risk Explanations**, **Recommendations**, **Approvals**, or **Model Evaluation**.")
