"""Recommendations Page: Ranked cost-sensitive financial interventions."""

import streamlit as st
import pandas as pd
from api_client import FinsightAPIClient

st.header("🎯 Policy-Compliant Recommendations & Expected Cost")

client: FinsightAPIClient = st.session_state.get("api_client", FinsightAPIClient())
account_id = st.session_state.get("selected_account_id", "ACC_001_STABLE")

try:
    risk = client.run_risk_assessment(account_id)
    proposals = client.get_recommendations(account_id)
except Exception as e:
    st.error(f"Failed to fetch recommendations: {e}")
    st.stop()

st.markdown(
    f"Interventions are ranked by **Expected Cost Reduction** under asymmetric error costs: "
    f"**C_FN = 5.0** (missed shortfall penalty) and **C_FP = 1.0** (unnecessary alert fatigue)."
)

if not proposals:
    st.success("✅ **No interventions required:** Account liquidity is stable and no shortfall is projected within 7 days.")
else:
    for idx, prop in enumerate(proposals, 1):
        with st.container(border=True):
            col_t, col_b = st.columns([3, 1])
            with col_t:
                st.markdown(f"### {idx}. {prop['title']}")
                st.markdown(f"**Action Category:** `{prop['action_type']}` | **Action ID:** `{prop['intervention_id']}`")
            with col_b:
                st.metric("Expected Benefit", f"{prop['expected_cost_benefit']:.2f} units")

            st.write(prop["description"])

            # Evidence & safety metadata
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            with meta_col1:
                st.markdown(f"**Mandatory Human Approval:** `{'Yes' if prop['mandatory_human_approval'] else 'No (Auto-Dispatched)'}`")
            with meta_col2:
                st.markdown(f"**Reversible:** `{'Yes' if prop['is_reversible'] else 'No'}`")
            with meta_col3:
                st.markdown(f"**Status:** `{prop['status']}`")

            with st.expander("Supporting Evidence & Proposed Changes"):
                st.markdown("**Evidence:**")
                for ev in prop.get("evidence_summary", []):
                    st.write(f"- {ev}")
                if prop.get("proposed_changes"):
                    st.markdown("**Proposed Changes Payload:**")
                    st.json(prop["proposed_changes"])

st.markdown("---")
st.subheader("🛡️ Non-Negotiable Safety Policy Commitments")
st.markdown("""
- **Essential Obligations Protected:** Rent, utilities, debt repayment, insurance, healthcare, and payroll cannot be cancelled or paused.
- **Zero Real Transfers:** No live bank transfers, loan approvals, or credit limit increases occur.
- **Mandatory Approvals:** All high-impact budget and bill actions require authenticated user confirmation.
""")
