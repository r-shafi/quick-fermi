"""FinSight AI — Upgraded Streamlit Dashboard Entry Point.

17-section navigation for the 2026 FinTechathon competition.
"""

import streamlit as st
import sys
import os

# Ensure frontend directory is on path so design_system can be imported from pages
sys.path.insert(0, os.path.dirname(__file__))

from design_system import inject_css, competition_banner, COLORS
from api_client import FinsightAPIClient

st.set_page_config(
    page_title="FinSight AI — SME Finance Copilot",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "FinSight AI: Cost-Sensitive, Explainable, Predictive Financial Intervention Agent — FinTechathon 2026",
    },
)

inject_css()

# ─── Initialize session state ─────────────────────────────────────────────────
if "api_client" not in st.session_state:
    st.session_state.api_client = FinsightAPIClient()
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False
if "demo_step" not in st.session_state:
    st.session_state.demo_step = 0

client: FinsightAPIClient = st.session_state.api_client

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand
    st.markdown(
        """
        <div style="text-align:center; padding: 16px 0 8px;">
            <div style="font-size:2rem;">🛡️</div>
            <div style="font-weight:700; font-size:1.1rem; color:#e2e8f0;">FinSight AI</div>
            <div style="font-size:0.72rem; color:#94a3b8; letter-spacing:0.06em; text-transform:uppercase;">SME Finance Copilot</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Backend health indicator
    try:
        health = client.check_health()
        api_status = health.get("status", "unknown")
        status_color = "#10b981" if api_status == "ok" else "#ef4444"
        st.markdown(
            f'<div style="text-align:center;font-size:0.72rem;color:{status_color};margin-bottom:8px;">● API {api_status.upper()}</div>',
            unsafe_allow_html=True,
        )
    except Exception:
        st.markdown(
            '<div style="text-align:center;font-size:0.72rem;color:#ef4444;margin-bottom:8px;">● API OFFLINE</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<hr/>", unsafe_allow_html=True)

    # Account selector
    try:
        accounts = client.list_accounts()
        account_ids = [a["account_id"] for a in accounts]
    except Exception:
        account_ids = ["ACC_001_STABLE", "ACC_002_SME"]

    selected_acc = st.selectbox(
        "Active Account",
        account_ids,
        index=0,
        key="selected_account_id_select",
        help="Select the SME account to analyse",
    )
    st.session_state.selected_account_id = selected_acc

    # Currency & mode badges
    st.markdown(
        f"""
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 12px;">
            <span style="font-size:0.7rem;background:#1e3a5f;color:#60a5fa;padding:2px 8px;border-radius:10px;font-weight:600;">BDT ৳</span>
            <span style="font-size:0.7rem;background:#2e1065;color:#c4b5fd;padding:2px 8px;border-radius:10px;font-weight:600;">SANDBOX</span>
            <span style="font-size:0.7rem;background:#064e3b;color:#34d399;padding:2px 8px;border-radius:10px;font-weight:600;">v0.2.0</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # CSV Upload
    with st.expander("📤 Upload Transaction CSV"):
        uploaded_file = st.file_uploader("Bank / ledger CSV", type=["csv"], label_visibility="collapsed")
        if uploaded_file is not None:
            is_sme = "SME" in selected_acc or "sme" in selected_acc.lower()
            if st.button("Process & Validate", use_container_width=True):
                with st.spinner("Ingesting and validating…"):
                    try:
                        rep = client.upload_csv(
                            file_bytes=uploaded_file.getvalue(),
                            filename=uploaded_file.name,
                            currency="BDT",
                            account_type="SME" if is_sme else "PERSONAL",
                        )
                        st.success(f"✅ {rep.get('valid_records', 0)} valid records ingested")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Upload failed: {err}")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # Demo mode toggle
    demo_label = "🎬 Exit Demo Mode" if st.session_state.demo_mode else "🎬 Launch Demo Mode"
    if st.button(demo_label, use_container_width=True):
        st.session_state.demo_mode = not st.session_state.demo_mode
        st.session_state.demo_step = 0
        st.rerun()

    if st.session_state.demo_mode:
        st.info("Demo mode active. Follow guided steps on the Competition Evidence page.", icon="🎬")

    st.markdown("<hr/>", unsafe_allow_html=True)

    # Navigation guide
    st.markdown(
        """
        <div style="font-size:0.7rem;color:#64748b;line-height:1.8;">
        <b style="color:#94a3b8;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;">Navigation</b><br/>
        Core Intelligence<br/>
        • Executive Overview<br/>
        • SME Command Center<br/>
        • Cash‑Flow Forecast<br/>
        • Risk Intelligence<br/>
        • AI Agent Workspace<br/>
        • Scenario Simulator<br/>
        • Approval Center<br/>
        • Model Lab<br/>
        <br/>
        Validation & Compliance<br/>
        • Financial Accuracy<br/>
        • Security & Compliance<br/>
        • Adversarial Testing<br/>
        • Data Quality<br/>
        • Model Drift<br/>
        • RL Research<br/>
        <br/>
        Evidence & Operations<br/>
        • Audit History<br/>
        • Competition Evidence<br/>
        • System Settings<br/>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.caption("FinTechathon 2026 · Shenzhen · Topic E")
    st.caption("Prototype: SANDBOX ONLY — No real transactions")

# ─── Main landing content ─────────────────────────────────────────────────────
competition_banner()

st.markdown(
    """
    <h1 style="font-size:2rem; font-weight:800; margin-bottom:8px;">
        🛡️ FinSight AI
        <span style="font-size:1rem; font-weight:400; color:#94a3b8; margin-left:12px;">SME Finance Copilot</span>
    </h1>
    <p style="color:#94a3b8; font-size:1rem; margin-bottom:24px;">
        Cost-sensitive, explainable, predictive financial intervention agent for SME liquidity management.
        Cost matrix: <code>C_FN = 5.0</code> · <code>C_FP = 1.0</code> · Safety buffer: <code>BDT 500</code>
    </p>
    """,
    unsafe_allow_html=True,
)

# Quick account summary bar
if selected_acc:
    try:
        summary = client.get_account_summary(selected_acc)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Available Balance", f"৳ {summary['available_balance']:,.0f}", help="Current verified available cash balance")
        c2.metric("Ledger Balance", f"৳ {summary['ledger_balance']:,.0f}", help="Recorded ledger balance")
        c3.metric("Transaction History", f"{summary['total_transactions']} txns", help="Total validated transactions loaded")
        c4.metric("Data Age", f"{summary['data_staleness_days']:.0f} days", help="Days since most recent transaction")
        c5.metric(
            "Account Status",
            "COLD START" if summary["is_cold_start"] else "MATURE",
            delta="<14 days data" if summary["is_cold_start"] else "≥14 days data",
            delta_color="inverse" if summary["is_cold_start"] else "normal",
        )
    except Exception as e:
        st.warning(f"Cannot load account summary: {e}. Ensure the backend API is running on port 8000.")

st.markdown("---")

# Module cards
st.markdown("### 📋 Available Modules")
cols = st.columns(4)
modules = [
    ("📊", "Executive Overview", "Full KPI dashboard with cash-flow timeline"),
    ("🏢", "SME Command Center", "Transaction explorer and reconciliation"),
    ("📈", "Cash-Flow Forecast", "Deterministic + Monte Carlo 14-day forecast"),
    ("🔍", "Risk Intelligence", "SHAP-explained shortfall probability"),
    ("🤖", "AI Agent Workspace", "Live agent execution trace and decision inspector"),
    ("🔬", "Scenario Simulator", "5 side-by-side what-if strategies"),
    ("✅", "Approval Center", "Human-in-the-loop intervention queue"),
    ("🧪", "Model Lab", "Multi-model comparison and cost-surface charts"),
    ("📋", "Financial Accuracy", "Evidence-grounded validation status"),
    ("🔒", "Security & Compliance", "OWASP/NIST posture dashboard"),
    ("⚔️", "Adversarial Testing", "12 attack scenarios with real pytest results"),
    ("🗄️", "Data Quality", "CSV validation, quality heatmaps, synthetic generator"),
    ("📡", "Model Drift", "PSI/ADWIN monitoring and version history"),
    ("🎓", "RL Research", "Offline policy comparison (experimental)"),
    ("📜", "Audit History", "Hash-chained immutable event explorer"),
    ("🏆", "Competition Evidence", "Requirements matrix + guided demo"),
    ("⚙️", "System Settings", "Configuration and role-based controls"),
]

for i, (icon, name, desc) in enumerate(modules):
    with cols[i % 4]:
        st.markdown(
            f"""
            <div class="finsight-card" style="min-height:90px;">
                <div style="font-size:1.4rem;">{icon}</div>
                <div style="font-weight:600;font-size:0.85rem;color:#e2e8f0;margin-top:4px;">{name}</div>
                <div style="font-size:0.75rem;color:#64748b;margin-top:3px;">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("---")
st.caption(
    "👈 Use the sidebar to navigate between modules. "
    "All data uses synthetic SME accounts. No real financial transactions are executed."
)
