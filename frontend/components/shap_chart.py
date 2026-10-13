"""Upgraded SHAP waterfall chart with dark theme and feature-value panel."""

from typing import Any, Dict, List, Optional
import plotly.graph_objects as go


DARK_BG = "rgba(10,22,40,0.95)"
DARK_PLOT = "rgba(15,32,68,0.8)"


def render_shap_waterfall(
    shap_contributions: List[Dict[str, Any]],
    baseline: float = 0.5,
    title: str = "Feature Contributions to Shortfall Risk",
) -> go.Figure:
    """Render a horizontal SHAP waterfall chart."""
    if not shap_contributions:
        fig = go.Figure()
        fig.update_layout(
            title="No SHAP explanation available",
            template="plotly_dark",
            paper_bgcolor=DARK_BG,
            plot_bgcolor=DARK_PLOT,
            height=300,
        )
        return fig

    # Sort by absolute contribution
    sorted_contribs = sorted(shap_contributions, key=lambda x: abs(x.get("shap_value", 0)), reverse=True)
    top_n = sorted_contribs[:12]

    features = [c.get("feature_name", c.get("feature", "unknown")) for c in top_n]
    values = [c.get("shap_value", 0.0) for c in top_n]
    colors = ["#ef4444" if v > 0 else "#10b981" for v in values]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values,
        y=features,
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.3f}" for v in values],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>SHAP: %{x:+.4f}<extra></extra>",
        name="SHAP Contribution",
    ))

    # Baseline reference
    fig.add_vline(
        x=0, line_dash="dash", line_color="#64748b", line_width=1,
        annotation_text=f"Baseline: {baseline:.2f}",
        annotation_position="top",
        annotation_font_color="#94a3b8",
        annotation_font_size=10,
    )

    fig.update_layout(
        title=title,
        xaxis_title="SHAP Value (impact on model output)",
        yaxis_title="Feature",
        height=max(300, len(top_n) * 30 + 100),
        template="plotly_dark",
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_PLOT,
        font=dict(family="Inter, Roboto, sans-serif", color="#e2e8f0", size=11),
        margin=dict(l=180, r=80, t=60, b=40),
        xaxis=dict(gridcolor="#1e3a6e", linecolor="#1e3a6e", zeroline=True, zerolinecolor="#334155"),
        yaxis=dict(gridcolor="#1e3a6e", linecolor="#1e3a6e", autorange="reversed"),
        bargap=0.3,
    )
    return fig


def render_risk_gauge(
    probability: float,
    threshold: float = 0.32,
    title: str = "Shortfall Risk",
) -> go.Figure:
    """Render a Plotly risk gauge indicator."""
    pct = round(probability * 100, 1)
    color = "#ef4444" if pct > 60 else "#f59e0b" if pct > 32 else "#10b981"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=pct,
        delta=dict(reference=threshold * 100, valueformat=".1f", suffix="%"),
        title=dict(text=title, font=dict(size=14, color="#e2e8f0")),
        number=dict(suffix="%", font=dict(size=28, color=color)),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor="#64748b", nticks=6),
            bar=dict(color=color, thickness=0.3),
            bgcolor="rgba(15,32,68,0.8)",
            borderwidth=1,
            bordercolor="#1e3a6e",
            steps=[
                dict(range=[0, 32], color="rgba(16,185,129,0.15)"),
                dict(range=[32, 60], color="rgba(245,158,11,0.15)"),
                dict(range=[60, 100], color="rgba(239,68,68,0.15)"),
            ],
            threshold=dict(
                line=dict(color="#f59e0b", width=3),
                thickness=0.8,
                value=threshold * 100,
            ),
        ),
    ))

    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor=DARK_BG,
        font=dict(color="#e2e8f0", family="Inter, sans-serif"),
    )
    return fig
