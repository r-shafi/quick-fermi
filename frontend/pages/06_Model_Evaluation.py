"""Model Evaluation Page: Temporal test metrics, baselines, and calibration."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from api_client import FinsightAPIClient

st.header("🧪 Reproducible Model Evaluation & Baselines")

client: FinsightAPIClient = st.session_state.get("api_client", FinsightAPIClient())

try:
    eval_data = client.get_model_evaluations()
except Exception as e:
    st.error(f"Failed to fetch model evaluation data: {e}")
    st.stop()

if eval_data.get("status") == "NOT_EVALUATED":
    st.warning("⚠️ **NOT EVALUATED:** Model training and evaluation have not yet run. Please run `make train` or `python scripts/train_models.py`.")
    st.stop()

# Prominent Provenance Disclaimer
st.info(f"ℹ️ **Evaluation Provenance:** {eval_data.get('disclaimer')} | Protocol: `{eval_data.get('evaluation_protocol')}`")

winner = eval_data.get("winner", "random_forest")
models = eval_data.get("models", {})

st.subheader(f"Winning Model: `{winner}` (Selected by Expected Financial Cost & Generalization)")

# Comparison Table
table_data = []
for name, m in models.items():
    table_data.append({
        "Model": name,
        "Test PR-AUC": f"{m.get('test_pr_auc', 0.0):.4f}",
        "Test ROC-AUC": f"{m.get('test_roc_auc', 0.0):.4f}",
        "Brier Score": f"{m.get('test_brier_score', 0.0):.4f}",
        "Expected Calibration Error (ECE)": f"{m.get('test_ece', 0.0):.4f}",
        "Optimal Decision Threshold": f"{m.get('optimal_threshold', 0.0):.4f}",
        "Expected Cost on Test Set": f"{m.get('test_expected_cost', 0.0):.2f}",
        "Recall @ 20% Alert Budget": f"{m.get('recall_at_20pct_budget', 0.0):.1%}",
    })

st.dataframe(pd.DataFrame(table_data), use_container_width=True)

# Confusion Matrix Comparison
st.subheader("Test Set Confusion Matrices")
cm_cols = st.columns(len(models))
for idx, (name, m) in enumerate(models.items()):
    with cm_cols[idx]:
        st.markdown(f"**{name}**")
        cm = m.get("confusion_matrix", {})
        st.write(f"True Positives: **{cm.get('TP')}**")
        st.write(f"True Negatives: **{cm.get('TN')}**")
        st.write(f"False Positives: **{cm.get('FP')}**")
        st.write(f"False Negatives: **{cm.get('FN')}**")

# Cost Comparison Bar Chart
st.subheader("Expected Financial Cost Comparison on Untouched Test Set")
model_names = list(models.keys())
costs = [models[m].get("test_expected_cost", 0.0) for m in model_names]

cost_fig = go.Figure(
    go.Bar(
        x=model_names,
        y=costs,
        marker_color=["#2980B9" if m == winner else "#BDC3C7" for m in model_names],
        text=[f"{c:.2f}" for c in costs],
        textposition="auto",
    )
)
cost_fig.update_layout(
    title="Total Expected Financial Cost (Lower is Better, C_FN=5.0, C_FP=1.0)",
    xaxis_title="Candidate Model",
    yaxis_title="Total Error Cost on Test Set",
    height=360,
)
st.plotly_chart(cost_fig, use_container_width=True)

with st.expander("Offline RL / Policy Evaluation"):
    try:
        policy_data = client.get_policy_evaluations()
        if policy_data.get("status") == "COMPLETED":
            st.markdown(f"**Policy Evaluation Method:** {policy_data.get('evaluation_method')}")
            st.markdown(f"**Sample Count:** {policy_data.get('dataset_samples')} simulated periods")
            st.caption(policy_data.get("disclaimer"))

            pol_rows = []
            for p_name, p_info in policy_data.get("policies", {}).items():
                pol_rows.append({
                    "Policy": p_name,
                    "Total Reward": f"{p_info.get('total_reward'):.2f}",
                    "Mean Reward per Period": f"{p_info.get('mean_reward'):.4f}",
                    "Shortfalls Prevented": f"{p_info.get('shortfalls_prevented')}/{p_info.get('total_shortfalls')}",
                    "Prevention Rate": f"{p_info.get('prevention_rate'):.1%}",
                })
            st.dataframe(pd.DataFrame(pol_rows), use_container_width=True)
    except Exception as e:
        st.write(f"Could not load policy evaluation: {e}")
