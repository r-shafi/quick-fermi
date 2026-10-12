"""Plotly SHAP feature contribution explanation chart."""

from typing import Any, Dict, List
import plotly.graph_objects as go


def render_shap_chart(
    top_drivers: List[Dict[str, Any]],
    top_mitigators: List[Dict[str, Any]],
) -> go.Figure:
    """Render horizontal bar chart of SHAP feature contributions."""
    features = []
    shap_values = []
    colors = []
    hover_texts = []

    # Add mitigators (negative impact on risk)
    for m in reversed(top_mitigators):
        features.append(m.get("human_description", m.get("feature_name")))
        val = m.get("shap_value", 0.0)
        shap_values.append(val)
        colors.append("#27AE60")
        hover_texts.append(f"Value: {m.get('feature_value', 0):.2f} | SHAP: {val:.4f} (Reduces Risk)")

    # Add drivers (positive impact on risk)
    for d in top_drivers:
        features.append(d.get("human_description", d.get("feature_name")))
        val = d.get("shap_value", 0.0)
        shap_values.append(val)
        colors.append("#E74C3C")
        hover_texts.append(f"Value: {d.get('feature_value', 0):.2f} | SHAP: +{val:.4f} (Increases Risk)")

    fig = go.Figure(
        go.Bar(
            x=shap_values,
            y=features,
            orientation="h",
            marker_color=colors,
            hovertext=hover_texts,
            hoverinfo="text",
        )
    )

    fig.update_layout(
        title="Key Factors Influencing Liquidity Risk (SHAP Feature Contributions)",
        xaxis_title="Impact on Model Shortfall Probability Score",
        yaxis={"autorange": "reversed"},
        height=380,
        margin={"l": 200, "r": 40, "t": 50, "b": 40},
        font={"family": "Inter, Roboto, sans-serif"},
    )
    return fig
