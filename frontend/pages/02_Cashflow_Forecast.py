"""Cashflow Forecast Page: Trajectory projections and prediction intervals."""

import streamlit as st
import pandas as pd
from api_client import FinsightAPIClient
from components.cashflow_chart import render_cashflow_chart

st.header("📈 Cash-Flow Forecast & Uncertainty Bands")

client: FinsightAPIClient = st.session_state.get("api_client", FinsightAPIClient())
account_id = st.session_state.get("selected_account_id", "ACC_001_STABLE")

col_mode, col_buffer = st.columns([2, 1])
with col_mode:
    method = st.radio("Forecasting Approach", ["probabilistic", "deterministic"], horizontal=True)
with col_buffer:
    safety_buffer = st.number_input("Safety Buffer Threshold (BDT)", value=500.0, step=100.0)

try:
    summary = client.get_account_summary(account_id)
    forecast = client.get_forecast(account_id, method=method)
except Exception as e:
    st.error(f"Failed to fetch forecast: {e}")
    st.stop()

# Plot interactive forecast chart
chart_fig = render_cashflow_chart(
    daily_intervals=forecast.get("daily_intervals" if method == "probabilistic" else "daily_balance_trajectory", []),
    current_balance=summary["available_balance"],
    currency=summary["currency"],
    safety_buffer=safety_buffer,
)
st.plotly_chart(chart_fig, use_container_width=True)

# Horizon breakdown table
st.subheader("Forecast Horizons Summary")
horizons_data = forecast.get("horizons", {})
table_rows = []
for h_str in ["1", "3", "7", "14"]:
    h_info = horizons_data.get(h_str, {})
    if h_info:
        table_rows.append({
            "Horizon": f"{h_str} Day(s)",
            "Projected Balance (BDT)": f"{h_info.get('projected_balance_median', h_info.get('projected_balance', 0)):,.2f}",
            "Lower Bound P10 (BDT)": f"{h_info.get('lower_bound_p10', '-'):,}" if 'lower_bound_p10' in h_info else "N/A",
            "Upper Bound P90 (BDT)": f"{h_info.get('upper_bound_p90', '-'):,}" if 'upper_bound_p90' in h_info else "N/A",
            "Known Scheduled Bills": f"BDT {h_info.get('known_obligations', 0):,.2f}",
            "Shortfall Probability": f"{h_info.get('probability_shortfall', 0.0):.1%}" if 'probability_shortfall' in h_info else ("Yes" if h_info.get('is_shortfall') else "No"),
        })

if table_rows:
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

with st.expander("Modeling Assumptions & Methodology"):
    st.markdown("""
    - **Deterministic roll-forward:** Projects balance using current verified balance, expected incoming salary/invoices, scheduled recurring obligations, and historical 30-day baseline discretionary spend.
    - **Probabilistic Monte Carlo:** Simulates 500 stochastic daily cash-flow trajectories based on empirical residual spending distributions to compute P10, P50, and P90 quantiles.
    - **No Double-Counting:** Known scheduled obligations (rent, utilities, payroll) are strictly separated from residual discretionary noise.
    """)
