"""Plotly cash-flow forecast chart with uncertainty bounds and obligations."""

from typing import Any, Dict, List
import plotly.graph_objects as go


def render_cashflow_chart(
    daily_intervals: List[Dict[str, Any]],
    current_balance: float,
    currency: str = "BDT",
    safety_buffer: float = 500.0,
) -> go.Figure:
    """Render cash-flow forecast trajectory with upper and lower quantile bands."""
    fig = go.Figure()

    if not daily_intervals:
        return fig

    dates = [x.get("date", f"Day {x.get('day')}") for x in daily_intervals]
    medians = [x.get("median_p50", x.get("projected_balance", 0.0)) for x in daily_intervals]
    lowers = [x.get("lower_p10", medians[i]) for i, x in enumerate(daily_intervals)]
    uppers = [x.get("upper_p90", medians[i]) for i, x in enumerate(daily_intervals)]
    obligations = [x.get("known_obligations", 0.0) for x in daily_intervals]

    # Upper bound
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=uppers,
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Lower bound with fill
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=lowers,
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor="rgba(52, 152, 219, 0.15)",
            name="80% Uncertainty Band (P10–P90)",
            hoverinfo="skip",
        )
    )

    # Median projected balance
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=medians,
            mode="lines+markers",
            name="Projected Balance (Median)",
            line={"color": "#2980B9", "width": 3},
            marker={"size": 6},
        )
    )

    # Minimum safety buffer line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=[safety_buffer] * len(dates),
            mode="lines",
            name=f"Minimum Safety Buffer ({currency} {safety_buffer:.0f})",
            line={"color": "#E74C3C", "width": 2, "dash": "dash"},
        )
    )

    # Known scheduled obligations bars on secondary axis or hover
    has_bills = any(b > 0 for b in obligations)
    if has_bills:
        fig.add_trace(
            go.Bar(
                x=dates,
                y=obligations,
                name="Known Scheduled Bills",
                marker_color="rgba(231, 76, 60, 0.4)",
                yaxis="y2",
            )
        )

    layout_kwargs = {
        "title": f"14-Day Forward Cash-Flow Forecast & Uncertainty ({currency})",
        "xaxis_title": "Forecast Date",
        "yaxis_title": f"Projected Balance ({currency})",
        "hovermode": "x unified",
        "height": 420,
        "margin": {"l": 40, "r": 40, "t": 50, "b": 40},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        "font": {"family": "Inter, Roboto, sans-serif"},
    }

    if has_bills:
        layout_kwargs["yaxis2"] = {
            "title": f"Obligations ({currency})",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        }

    fig.update_layout(**layout_kwargs)
    return fig
