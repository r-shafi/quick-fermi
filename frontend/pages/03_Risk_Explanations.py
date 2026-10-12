"""Risk Explanations Page: SHAP feature contributions and verified evidence narrative."""

import streamlit as st
from api_client import FinsightAPIClient
from components.shap_chart import render_shap_chart

st.header("🔍 Explainable Risk Breakdown & Evidence")

client: FinsightAPIClient = st.session_state.get("api_client", FinsightAPIClient())
account_id = st.session_state.get("selected_account_id", "ACC_001_STABLE")

try:
    risk = client.run_risk_assessment(account_id)
    expl = client.get_explanations(account_id)
except Exception as e:
    st.error(f"Failed to fetch explanations: {e}")
    st.stop()

# Probability & Calibration Callout
col1, col2, col3 = st.columns(3)
col1.metric("Predicted Shortfall Risk", f"{risk['calibrated_probability']:.1%}")
col2.metric("Decision Threshold (τ*)", f"{risk['decision_threshold']:.1%}")
col3.metric("Calibration Method", "Isotonic Regression (Holdout-Fitted)")

# Verified Plain-Language Narrative
st.subheader("Verified Model Evidence Narrative")
narrative = expl.get("deterministic_narrative", "Model evaluation complete.")
st.info(f"**Analyst Finding:** {narrative}")

# SHAP Bar Chart
st.subheader("Feature Contribution Breakdown (SHAP)")
drivers = expl.get("top_risk_drivers", [])
mitigators = expl.get("top_risk_mitigators", [])

if drivers or mitigators:
    shap_fig = render_shap_chart(top_drivers=drivers, top_mitigators=mitigators)
    st.plotly_chart(shap_fig, use_container_width=True)
else:
    st.write("No SHAP values available for this model state.")

# Structured Drivers & Mitigators side by side
col_d, col_m = st.columns(2)
with col_d:
    st.markdown("### 🔴 Top Factors Increasing Risk")
    for d in drivers:
        st.markdown(
            f"- **{d.get('human_description', d.get('feature_name'))}**: "
            f"Value = `{d.get('feature_value')}` (SHAP contribution: `+{d.get('shap_value'):.4f}`)"
        )

with col_m:
    st.markdown("### 🟢 Top Factors Mitigating Risk")
    for m in mitigators:
        st.markdown(
            f"- **{m.get('human_description', m.get('feature_name'))}**: "
            f"Value = `{m.get('feature_value')}` (SHAP contribution: `{m.get('shap_value'):.4f}`)"
        )

with st.expander("Model Card Limitations & Interpretability Disclaimers"):
    for lim in expl.get("limitations", []):
        st.write(f"- {lim}")
