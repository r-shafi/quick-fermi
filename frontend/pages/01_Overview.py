"""Overview Page: Account health, liquidity summary, and real-time shortfall risk."""

import streamlit as st
from api_client import FinsightAPIClient
from components.risk_gauge import render_risk_gauge

st.header("📊 Account Health & Liquidity Overview")

client: FinsightAPIClient = st.session_state.get("api_client", FinsightAPIClient())
account_id = st.session_state.get("selected_account_id", "ACC_001_STABLE")

try:
    summary = client.get_account_summary(account_id)
    risk = client.run_risk_assessment(account_id)
    forecast = client.get_forecast(account_id, method="probabilistic")
except Exception as e:
    st.error(f"Failed to fetch account overview: {e}")
    st.stop()

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Liquidity Status")
    st.metric("Current Verified Balance", f"BDT {summary['available_balance']:,.2f}")

    h7 = forecast.get("horizons", {}).get("7", {})
    min_7d = h7.get("projected_balance_median", summary["available_balance"])
    st.metric("Projected 7-Day Balance", f"BDT {min_7d:,.2f}")

    if summary["is_cold_start"]:
        st.warning("⚠️ **INSUFFICIENT_HISTORY:** This account has limited observed history. Predictions apply bounded conservative priors.")

    with st.expander("Data Quality & Observability Metrics"):
        st.write(f"- Total Recorded Transactions: **{summary['total_transactions']}**")
        st.write(f"- Observed History Window: **{summary['history_days']} days**")
        st.write(f"- Data Staleness: **{summary['data_staleness_days']} days**")
        st.write(f"- Account Type: **{summary['account_type']}**")
        st.write(f"- Currency: **{summary['currency']}**")

with col_right:
    st.subheader("Shortfall Risk Indicator")
    gauge_fig = render_risk_gauge(
        probability=risk["calibrated_probability"],
        threshold=risk["decision_threshold"],
        risk_level=risk["risk_level"],
    )
    st.plotly_chart(gauge_fig, use_container_width=True)

    st.markdown(
        f"**Decision Threshold:** `{risk['decision_threshold']:.1%}` | "
        f"**Model Name:** `{risk['model_name']}` (`v{risk['model_version']}`)"
    )

    if risk["is_shortfall_predicted"]:
        st.error(
            f"🚨 **Action Warranted:** Calibrated risk ({risk['calibrated_probability']:.1%}) "
            f"exceeds optimal decision threshold ({risk['decision_threshold']:.1%}). "
            f"Expected cost of inaction: **{risk['expected_cost_of_inaction']:.2f} relative units**."
        )
    else:
        st.success(
            f"✅ **Liquidity Healthy:** Calibrated risk ({risk['calibrated_probability']:.1%}) "
            f"remains below decision threshold ({risk['decision_threshold']:.1%})."
        )
