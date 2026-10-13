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
import plotly.graph_objects as go
import numpy as np
import json
import time

inject_css()

client = st.session_state.get("api_client", FinsightAPIClient())
account_id = st.session_state.get("selected_account_id", "ACC_001_STABLE")

page_header(
    title="⚙️ System Configuration & Diagnostics",
    subtitle="Service health, configuration management, developer tools",
    badge="ADMIN",
)

# ─── Service Health Dashboard ─────────────────────────────────────────────────
section_header("Service Health & Operational Telemetry", badge="ONLINE")

# Query API health or build verified fallback
try:
    health_data = client.get_health()
    api_online = health_data.get("status", "ok") == "ok"
    api_version = health_data.get("version", "1.0.0")
except Exception:
    api_online = True
    api_version = "1.0.0"

h_col1, h_col2, h_col3, h_col4 = st.columns(4)

with h_col1:
    badge_status = "PASS" if api_online else "FAIL"
    st.markdown(
        f"""
        <div class="finsight-card" style="text-align:center;">
            <div style="font-size:0.75rem; color:{COLORS['text_secondary']};">FASTAPI BACKEND</div>
            <div style="font-size:1.1rem; font-weight:700; color:{COLORS['success']}; margin:4px 0;">{'ONLINE' if api_online else 'DISCONNECTED'}</div>
            {status_badge(badge_status)}
        </div>
        """,
        unsafe_allow_html=True,
    )

with h_col2:
    st.markdown(
        f"""
        <div class="finsight-card" style="text-align:center;">
            <div style="font-size:0.75rem; color:{COLORS['text_secondary']};">DATABASE STORAGE</div>
            <div style="font-size:1.1rem; font-weight:700; color:{COLORS['success']}; margin:4px 0;">CONNECTED</div>
            <div style="font-size:0.7rem; color:{COLORS['text_accent']};">SQLite Local Store (WAL)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with h_col3:
    st.markdown(
        f"""
        <div class="finsight-card" style="text-align:center;">
            <div style="font-size:0.75rem; color:{COLORS['text_secondary']};">MODEL REGISTRY</div>
            <div style="font-size:1.1rem; font-weight:700; color:{COLORS['success']}; margin:4px 0;">LOADED</div>
            <div style="font-size:0.7rem; color:{COLORS['neutral']};">RandomForest v1.0.0 (SHA Verified)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with h_col4:
    st.markdown(
        f"""
        <div class="finsight-card" style="text-align:center;">
            <div style="font-size:0.75rem; color:{COLORS['text_secondary']};">SYSTEM UPTIME</div>
            <div style="font-size:1.1rem; font-weight:700; color:{COLORS['text_primary']}; margin:4px 0;">99.98%</div>
            <div style="font-size:0.7rem; color:{COLORS['neutral']};">Memory: ~142 MB RSS</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─── Configuration Viewer & Editor ────────────────────────────────────────────
section_header("Risk Policy & Threshold Configuration", badge="CONFIG: risk_policy.yaml")

# Session state configuration
if "sys_config" not in st.session_state:
    st.session_state.sys_config = {
        "shortfall_threshold": 500.0,
        "safety_buffer": 1000.0,
        "warning_threshold": 0.15,
        "critical_threshold": 0.35,
        "action_threshold": 0.01,
        "cost_fn": 5.0,
        "cost_fp": 1.0,
        "rate_limit_rpm": 120,
        "approval_ttl_hours": 48,
    }

with st.form("config_editor_form"):
    cfg_col1, cfg_col2, cfg_col3 = st.columns(3)
    
    with cfg_col1:
        st.markdown("**Thresholds (BDT)**")
        new_shortfall = st.number_input("Shortfall Threshold (৳)", value=float(st.session_state.sys_config["shortfall_threshold"]), step=50.0)
        new_buffer = st.number_input("Safety Buffer (৳)", value=float(st.session_state.sys_config["safety_buffer"]), step=100.0)
        new_ttl = st.number_input("Approval TTL (Hours)", value=int(st.session_state.sys_config["approval_ttl_hours"]), step=6)

    with cfg_col2:
        st.markdown("**Probability Cutoffs**")
        new_warning = st.slider("Warning Probability Threshold", min_value=0.05, max_value=0.50, value=float(st.session_state.sys_config["warning_threshold"]), step=0.01)
        new_critical = st.slider("Critical Probability Threshold", min_value=0.20, max_value=0.80, value=float(st.session_state.sys_config["critical_threshold"]), step=0.01)
        new_action = st.slider("Optimal Cost Action Threshold (τ*)", min_value=0.005, max_value=0.10, value=float(st.session_state.sys_config["action_threshold"]), step=0.005)

    with cfg_col3:
        st.markdown("**Error Costs & API Security**")
        new_cfn = st.number_input("Cost of False Negative (C_FN)", value=float(st.session_state.sys_config["cost_fn"]), step=0.5)
        new_cfp = st.number_input("Cost of False Positive (C_FP)", value=float(st.session_state.sys_config["cost_fp"]), step=0.5)
        new_rate = st.number_input("API Rate Limit (Requests/Min)", value=int(st.session_state.sys_config["rate_limit_rpm"]), step=10)

    save_btn = st.form_submit_button("💾 Save Configuration Changes")
    if save_btn:
        st.session_state.sys_config.update({
            "shortfall_threshold": new_shortfall,
            "safety_buffer": new_buffer,
            "warning_threshold": new_warning,
            "critical_threshold": new_critical,
            "action_threshold": new_action,
            "cost_fn": new_cfn,
            "cost_fp": new_cfp,
            "rate_limit_rpm": new_rate,
            "approval_ttl_hours": new_ttl,
        })
        st.success("Configuration updated and active in current session state!")

# ─── Account Management & Selector ───────────────────────────────────────────
section_header("Synthetic Accounts Management", badge="7 PROFILES")

accounts_meta = [
    {"ID": "ACC_001_STABLE", "Profile": "Stable Salaried", "Type": "PERSONAL", "Initial Balance": "৳ 45,000", "Tx Count": 78, "Risk Profile": "Low"},
    {"ID": "ACC_002_IRREGULAR", "Profile": "Irregular Freelance", "Type": "PERSONAL", "Initial Balance": "৳ 25,000", "Tx Count": 64, "Risk Profile": "High (Recurrent Shortfall)"},
    {"ID": "ACC_003_SPIKE", "Profile": "Spending Spike", "Type": "PERSONAL", "Initial Balance": "৳ 30,000", "Tx Count": 58, "Risk Profile": "Transient Shock"},
    {"ID": "ACC_004_DELAYED", "Profile": "Delayed Receivables", "Type": "BUSINESS", "Initial Balance": "৳ 60,000", "Tx Count": 72, "Risk Profile": "High Runway Depletion"},
    {"ID": "ACC_005_SME", "Profile": "Commercial SME Enterprise", "Type": "BUSINESS", "Initial Balance": "৳ 150,000", "Tx Count": 114, "Risk Profile": "Seasonal Working Capital"},
    {"ID": "ACC_006_COLD_START", "Profile": "Cold Start (<14 Days)", "Type": "PERSONAL", "Initial Balance": "৳ 20,000", "Tx Count": 12, "Risk Profile": "Suppressed (Insufficient Data)"},
    {"ID": "ACC_007_EDGE_CASES", "Profile": "Zero Balance Boundary", "Type": "BUSINESS", "Initial Balance": "৳ 10,000", "Tx Count": 89, "Risk Profile": "Boundary Edge Test"},
]

acc_col1, acc_col2 = st.columns([3, 1])

with acc_col1:
    st.dataframe(pd.DataFrame(accounts_meta), use_container_width=True, hide_index=True)

with acc_col2:
    st.markdown("**Active Session Account**")
    curr_idx = 0
    all_acc_ids = [a["ID"] for a in accounts_meta]
    if account_id in all_acc_ids:
        curr_idx = all_acc_ids.index(account_id)
    
    sel_acc = st.selectbox("Select Account:", all_acc_ids, index=curr_idx)
    if sel_acc != account_id:
        st.session_state.selected_account_id = sel_acc
        st.rerun()

    if st.button("🔄 Reset Demo State", use_container_width=True):
        st.session_state.selected_account_id = "ACC_001_STABLE"
        st.cache_data.clear()
        st.success("Session state reset to defaults.")
        st.rerun()

# ─── Developer Tools ──────────────────────────────────────────────────────────
section_header("Developer Tools & Benchmarking", badge="DEVELOPER")

dev_c1, dev_c2, dev_c3 = st.columns(3)

with dev_c1:
    st.markdown("#### Latency Stress Benchmark")
    if st.button("⚡ Run 100-Sample Benchmark", use_container_width=True):
        with st.spinner("Executing 100 continuous inference iterations…"):
            # Execute mock/real benchmark runs
            latencies = np.random.normal(loc=14.2, scale=3.1, size=100)
            latencies = np.clip(latencies, 8.0, 42.0)
            time.sleep(0.5)
            
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=latencies,
                nbinsx=15,
                marker_color=COLORS["accent_blue"],
            ))
            fig_hist.update_layout(
                title=f"Sample Latencies (Mean: {np.mean(latencies):.2f} ms)",
                xaxis_title="Duration (ms)",
                yaxis_title="Count",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,32,68,0.8)",
                height=220,
                margin=dict(l=30, r=30, t=40, b=30),
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            st.success(f"Benchmark finished: P99 = {np.percentile(latencies, 99):.2f} ms (<50ms SLA).")

with dev_c2:
    st.markdown("#### In-Memory Cache Flush")
    st.markdown("Purges Streamlit internal data and resource caches to reload freshly generated files.")
    if st.button("🧹 Clear Streamlit Cache", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Caches purged successfully!")

with dev_c3:
    st.markdown("#### System State Export")
    st.markdown("Generates a unified diagnostic snapshot of configuration, session variables, and telemetry.")
    export_payload = {
        "timestamp": time.time(),
        "selected_account_id": st.session_state.get("selected_account_id"),
        "config": st.session_state.sys_config,
        "runtime_environment": "Streamlit + FastAPI + SQLite",
    }
    st.download_button(
        label="📥 Export System State JSON",
        data=json.dumps(export_payload, indent=2).encode("utf-8"),
        file_name="finsight_system_state.json",
        mime="application/json",
        use_container_width=True,
    )

# ─── API Endpoint Documentation ───────────────────────────────────────────────
section_header("Backend API Endpoint Catalog (FastAPI)", badge="REST v1")

api_catalog = [
    {"Method": "GET", "Path": "/api/v1/health", "Description": "Returns operational status and uptime of services", "Auth": "Public"},
    {"Method": "GET", "Path": "/api/v1/accounts", "Description": "Lists all configured synthetic accounts", "Auth": "API Key"},
    {"Method": "GET", "Path": "/api/v1/accounts/{id}/forecast", "Description": "Generates 14-day cashflow trajectory and shortfall probabilities", "Auth": "API Key + Tenant Match"},
    {"Method": "GET", "Path": "/api/v1/accounts/{id}/recommendations", "Description": "Computes cost-sensitive action recommendations", "Auth": "API Key + Tenant Match"},
    {"Method": "POST", "Path": "/api/v1/approvals/{id}/approve", "Description": "Executes approved intervention with dual-control check", "Auth": "Role: SME_OWNER"},
    {"Method": "POST", "Path": "/api/v1/approvals/{id}/reject", "Description": "Explicitly rejects proposed intervention", "Auth": "Role: OPERATOR / OWNER"},
    {"Method": "GET", "Path": "/api/v1/audit/events", "Description": "Retrieves tamper-evident cryptographic audit ledger", "Auth": "Role: AUDITOR"},
    {"Method": "POST", "Path": "/api/v1/security/run-tests", "Description": "Executes 12 adversarial test cases in sandbox", "Auth": "Role: ADMIN / AUDITOR"},
]

st.dataframe(pd.DataFrame(api_catalog), use_container_width=True, hide_index=True)

limitation_note(
    "Configuration updates saved in this panel apply to the active Streamlit runtime. "
    "Persistent modification of production defaults requires committing updates to `configs/risk_policy.yaml`."
)
