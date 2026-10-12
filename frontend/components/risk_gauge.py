"""Plotly gauge component displaying shortfall probability and decision threshold."""

import plotly.graph_objects as go


def render_risk_gauge(probability: float, threshold: float, risk_level: str) -> go.Figure:
    """Create a polished risk gauge chart."""
    prob_pct = probability * 100.0
    thresh_pct = threshold * 100.0

    color_map = {
        "LOW": "#2ECC71",
        "MODERATE": "#F39C12",
        "HIGH": "#E67E22",
        "CRITICAL": "#E74C3C",
    }
    bar_color = color_map.get(risk_level, "#3498DB")

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=prob_pct,
            number={"suffix": "%", "font": {"size": 36, "color": bar_color}},
            title={"text": f"7-Day Shortfall Probability ({risk_level})", "font": {"size": 18}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#BDC3C7"},
                "bar": {"color": bar_color, "thickness": 0.3},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": "#E0E0E0",
                "steps": [
                    {"range": [0, thresh_pct], "color": "#E8F8F5"},
                    {"range": [thresh_pct, 40], "color": "#FEF9E7"},
                    {"range": [40, 70], "color": "#FBEEE6"},
                    {"range": [70, 100], "color": "#FDEDEC"},
                ],
                "threshold": {
                    "line": {"color": "#C0392B", "width": 4},
                    "thickness": 0.8,
                    "value": thresh_pct,
                },
            },
        )
    )

    fig.update_layout(
        height=260,
        margin={"l": 30, "r": 30, "t": 40, "b": 20},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, Roboto, sans-serif"},
    )
    return fig
