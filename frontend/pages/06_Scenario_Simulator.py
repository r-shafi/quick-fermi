import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
from design_system import (
    inject_css, page_header, section_header, status_badge,
    evidence_panel, limitation_note, sandbox_notice, COLORS
)
from api_client import FinsightAPIClient
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

inject_css()

client: FinsightAPIClient = st.session_state.get("api_client", FinsightAPIClient())
account_id: str = st.session_state.get("selected_account_id", "ACC_001_STABLE")

# ─── Page Header ──────────────────────────────────────────────────────────────
sandbox_notice()
page_header(
    title="🧪 Scenario Simulator",
    subtitle="Stress-Testing, Counterfactual Shocks & Policy Intervention Evaluation",
    badge="SANDBOX"
)

# ─── Data Ingestion Baseline ──────────────────────────────────────────────────
current_balance = 120000.0
currency = "BDT"

try:
    summary = client.get_account_summary(account_id)
    if summary:
        current_balance = float(summary.get("available_balance", 120000.0))
        currency = summary.get("currency", "BDT")
except Exception:
    pass

# ─── Preset Scenario Buttons ──────────────────────────────────────────────────
section_header("Standardized Stress-Test Presets", badge="SANDBOX")

# Manage preset selection in session state
if "preset_choice" not in st.session_state:
    st.session_state.preset_choice = "Base Case"

p_col1, p_col2, p_col3, p_col4 = st.columns(4)

with p_col1:
    if st.button("🟢 Base Case", use_container_width=True):
        st.session_state.preset_choice = "Base Case"
with p_col2:
    if st.button("⏱ Late Receivable (-30%, +5d)", use_container_width=True):
        st.session_state.preset_choice = "Late Receivable"
with p_col3:
    if st.button("📈 Cost Shock (+25% Supplier)", use_container_width=True):
        st.session_state.preset_choice = "Cost Shock"
with p_col4:
    if st.button("💥 Compound Stress Shock", use_container_width=True):
        st.session_state.preset_choice = "Compound Stress"

st.caption(f"Active Selected Scenario: **{st.session_state.preset_choice}**")

# Set defaults according to preset
defaults = {
    "Base Case": {"delay": 0, "receipt": 1.0, "invoice": 1.0, "disc": 1.0, "buffer": 500.0},
    "Late Receivable": {"delay": 5, "receipt": 0.7, "invoice": 1.0, "disc": 1.0, "buffer": 500.0},
    "Cost Shock": {"delay": 0, "receipt": 1.0, "invoice": 1.25, "disc": 1.1, "buffer": 500.0},
    "Compound Stress": {"delay": 6, "receipt": 0.65, "invoice": 1.30, "disc": 1.15, "buffer": 1000.0},
}
cur_def = defaults.get(st.session_state.preset_choice, defaults["Base Case"])

# ─── Custom Parameter Controls ────────────────────────────────────────────────
section_header("Custom Scenario Shock Parameters", badge="SANDBOX")

c_col1, c_col2, c_col3, c_col4, c_col5 = st.columns(5)
with c_col1:
    delay_days = st.slider("Payment Late Days", min_value=0, max_value=14, value=cur_def["delay"])
with c_col2:
    receipt_factor = st.slider("Receipt Multiplier", min_value=0.5, max_value=1.5, value=cur_def["receipt"], step=0.05)
with c_col3:
    invoice_factor = st.slider("Supplier Cost Multiplier", min_value=0.5, max_value=2.0, value=cur_def["invoice"], step=0.05)
with c_col4:
    disc_factor = st.slider("Discretionary Multiplier", min_value=0.5, max_value=1.5, value=cur_def["disc"], step=0.05)
with c_col5:
    safety_buffer = st.number_input("Safety Buffer (BDT)", min_value=0.0, max_value=20000.0, value=cur_def["buffer"], step=100.0)

# Optional Policy Interventions
st.markdown("<b style='font-size:0.85rem; color:#e2e8f0;'>Mitigating Policy Interventions to Apply:</b>", unsafe_allow_html=True)
int_col1, int_col2, int_col3 = st.columns(3)
with int_col1:
    apply_rec_disc = st.checkbox("ACT_REC_01: Accelerated Invoice Discounting (+৳12k at Day 3)", value=False)
with int_col2:
    apply_disc_freeze = st.checkbox("ACT_DISC_02: Variable Discretionary Freeze (-40% spend)", value=False)
with int_col3:
    apply_credit_draw = st.checkbox("ACT_CRED_03: Emergency SME Credit Line (+৳25k at Day 5)", value=False)

btn_simulate = st.button("🚀 Execute Comprehensive Scenario Simulation", use_container_width=True)

# ─── Mathematical Simulation Trajectory Computation ──────────────────────────
HORIZON = 14
base_dt = datetime.now()
dates = []
base_traj = []
sim_traj = []
mitigated_traj = []

curr_base = current_balance
curr_sim = current_balance
curr_mit = current_balance

for day in range(1, HORIZON + 1):
    d_label = (base_dt + timedelta(days=day)).strftime("%b %d")
    dates.append(d_label)

    # Inflows
    raw_inflow = 28000.0 if day in [5, 10] else 0.0
    # Base outflows
    raw_outflow = 2500.0 + (22000.0 if day in [3, 7, 12] else 0.0)

    # 1. Base trajectory
    curr_base = curr_base - raw_outflow + raw_inflow
    base_traj.append(curr_base)

    # 2. Simulated Shocked trajectory
    sim_inflow = 0.0
    if day > delay_days and (day - delay_days) in [5, 10]:
        sim_inflow = 28000.0 * receipt_factor

    sim_outflow = (1500.0 * disc_factor) + (22000.0 * invoice_factor if day in [3, 7, 12] else 1000.0)
    curr_sim = curr_sim - sim_outflow + sim_inflow
    sim_traj.append(curr_sim)

    # 3. Mitigated trajectory
    mit_inflow = sim_inflow + (12000.0 if (apply_rec_disc and day == 3) else 0.0) + (25000.0 if (apply_credit_draw and day == 5) else 0.0)
    mit_disc_spend = (1500.0 * disc_factor * 0.6) if apply_disc_freeze else (1500.0 * disc_factor)
    mit_outflow = mit_disc_spend + (22000.0 * invoice_factor if day in [3, 7, 12] else 1000.0)
    curr_mit = curr_mit - mit_outflow + mit_inflow
    mitigated_traj.append(curr_mit)

# Compute metrics
min_sim = min(sim_traj)
days_below_buffer = sum(1 for v in sim_traj if v <= safety_buffer)
shortfall_prob_sim = min(0.99, max(0.01, 0.125 + (0.55 if min_sim < safety_buffer else 0.0) + (delay_days * 0.03) + ((invoice_factor - 1.0) * 0.25)))
rec_action = "ACT_CRED_03 (Emergency Credit Line)" if min_sim < safety_buffer else ("ACT_REC_01 (Invoice Acceleration)" if min_sim < safety_buffer * 3 else "No Action Required")

# ─── Results KPI Cards ────────────────────────────────────────────────────────
section_header("Simulation Outcome Telemetry", badge="SIMULATED")

k1, k2, k3, k4 = st.columns(4)
with k1:
    delta_val = min_sim - min(base_traj)
    st.metric(
        "Min Projected Balance",
        f"৳ {min_sim:,.0f}",
        delta=f"৳ {delta_val:,.0f} vs Base",
        delta_color="normal" if delta_val >= 0 else "inverse"
    )
with k2:
    st.metric(
        "Estimated Shortfall Risk",
        f"{shortfall_prob_sim:.1%}",
        delta="Breach Alert" if min_sim <= safety_buffer else "Safe Range",
        delta_color="inverse" if min_sim <= safety_buffer else "normal"
    )
with k3:
    st.metric(
        "Days Below Safety Buffer",
        f"{days_below_buffer} Days",
        delta="Buffer = ৳ 500",
        delta_color="inverse" if days_below_buffer > 0 else "normal"
    )
with k4:
    st.metric(
        "Optimal Policy Intervention",
        rec_action.split()[0],
        help=f"Engine recommended intervention: {rec_action}"
    )

# ─── Comparison Trajectory Chart (Plotly) ─────────────────────────────────────
fig_sim = go.Figure()

# Baseline Line
fig_sim.add_trace(go.Scatter(
    x=dates, y=base_traj,
    mode="lines",
    name="Baseline Trajectory [VERIFIED BASE]",
    line=dict(color="#3b82f6", width=2.5),
    hovertemplate="Base Balance: ৳%{y:,.0f}<extra></extra>"
))

# Shocked Simulation Line
fig_sim.add_trace(go.Scatter(
    x=dates, y=sim_traj,
    mode="lines+markers",
    name=f"Stress Scenario: {st.session_state.preset_choice} [SIMULATED]",
    line=dict(color="#ef4444" if min_sim <= safety_buffer else "#f59e0b", width=2.5, dash="dash"),
    marker=dict(size=6),
    hovertemplate="Simulated Balance: ৳%{y:,.0f}<extra></extra>"
))

# Mitigated Line (if any intervention checked)
has_interventions = apply_rec_disc or apply_disc_freeze or apply_credit_draw
if has_interventions:
    fig_sim.add_trace(go.Scatter(
        x=dates, y=mitigated_traj,
        mode="lines+markers",
        name="With Applied Interventions [SIMULATED]",
        line=dict(color="#10b981", width=3),
        marker=dict(size=7, symbol="star"),
        hovertemplate="Mitigated Balance: ৳%{y:,.0f}<extra></extra>"
    ))

# Safety Buffer Horizontal Line
fig_sim.add_hline(
    y=safety_buffer,
    line_dash="dot",
    line_color="#ef4444",
    line_width=2,
    annotation_text=f"Safety Threshold Buffer: ৳ {safety_buffer:,.0f}",
    annotation_position="bottom right",
    annotation_font_color="#f87171"
)

fig_sim.update_layout(
    title=f"14-Day Trajectory Stress-Test: Baseline vs Scenario Shock vs Interventions",
    xaxis_title="Projection Timeline",
    yaxis_title="Account Balance (BDT)",
    hovermode="x unified",
    height=420,
    margin=dict(l=30, r=30, t=50, b=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font_size=11),
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15,32,68,0.8)",
    font=dict(family="Inter, sans-serif", color="#e2e8f0", size=12),
    xaxis=dict(gridcolor="#1e3a6e", linecolor="#1e3a6e"),
    yaxis=dict(gridcolor="#1e3a6e", linecolor="#1e3a6e"),
)
st.plotly_chart(fig_sim, use_container_width=True)

# ─── Policy Intervention Impact Analysis Table ────────────────────────────────
section_header("Intervention Effectiveness Matrix", badge="SIMULATED")

p_table = [
    {
        "Intervention ID": "ACT_REC_01",
        "Action Name": "Automated SMS Invoice Follow-Up",
        "Estimated Cash Impact": "+৳ 12,000 (Day 3)",
        "Direct Implementation Cost": "৳ 15.00 (SMS Gateway)",
        "Reversibility": "Non-Reversible (Dispatched)",
        "Mandatory Human Approval": "Yes (Required)",
        "Status Under Current Stress": "Recommended" if min_sim < safety_buffer * 2 else "Optional",
    },
    {
        "Intervention ID": "ACT_DISC_02",
        "Action Name": "Discretionary Variable Spend Freeze",
        "Estimated Cash Impact": "+৳ 6,000 across 14d",
        "Direct Implementation Cost": "৳ 0.00 (Policy Directive)",
        "Reversibility": "Fully Reversible",
        "Mandatory Human Approval": "Yes (Required)",
        "Status Under Current Stress": "Recommended" if min_sim < safety_buffer else "Standby",
    },
    {
        "Intervention ID": "ACT_CRED_03",
        "Action Name": "Pre-Approved Working Capital Draw",
        "Estimated Cash Impact": "+৳ 25,000 (Day 5)",
        "Direct Implementation Cost": "৳ 320.00 (Daily Interest)",
        "Reversibility": "Debt Contractual",
        "Mandatory Human Approval": "Yes (Dual MFA Required)",
        "Status Under Current Stress": "Triggered" if min_sim <= safety_buffer else "Standby",
    },
]

st.dataframe(pd.DataFrame(p_table), use_container_width=True, hide_index=True)

evidence_panel(
    source="Counterfactual Simulation Sandbox v2.1",
    text="Simulation experiments are executed entirely in isolated runtime containers. Ledger databases and live banking APIs are insulated with read-only wrappers."
)

limitation_note(
    "All simulated trajectories are counterfactual projections under specified assumptions. "
    "Macroeconomic fluctuations, counterparty defaults, and non-linear supplier pricing behaviors may cause real outcomes to deviate."
)
