"""Upgraded Plotly cash-flow chart with dark theme and full annotation support."""

from typing import Any, Dict, List, Optional
import plotly.graph_objects as go


DARK_BG = "rgba(10,22,40,0.95)"
DARK_PLOT = "rgba(15,32,68,0.8)"


def render_cashflow_chart(
    daily_intervals: List[Dict[str, Any]],
    current_balance: float,
    currency: str = "BDT",
    safety_buffer: float = 500.0,
    title: Optional[str] = None,
    show_shortfall_zone: bool = True,
    highlight_color: str = "#3b82f6",
) -> go.Figure:
    """Render cash-flow forecast with dark theme, uncertainty fan, and event annotations."""
    fig = go.Figure()

    if not daily_intervals:
        fig.update_layout(
            title="No forecast data available",
            template="plotly_dark",
            paper_bgcolor=DARK_BG,
            plot_bgcolor=DARK_PLOT,
            height=400,
        )
        return fig

    dates = [x.get("date", f"Day {x.get('day', i)}") for i, x in enumerate(daily_intervals)]
    medians = [x.get("median_p50", x.get("projected_balance", 0.0)) for x in daily_intervals]
    lowers = [x.get("lower_p10", medians[i]) for i, x in enumerate(daily_intervals)]
    uppers = [x.get("upper_p90", medians[i]) for i, x in enumerate(daily_intervals)]
    obligations = [x.get("known_obligations", 0.0) for x in daily_intervals]

    # ── Uncertainty band (fill between p10 and p90) ──
    fig.add_trace(go.Scatter(
        x=dates, y=uppers,
        mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
        name="p90",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=lowers,
        mode="lines", line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(59,130,246,0.12)",
        name="80% Forecast Band (P10–P90)",
        hovertemplate="P10–P90: %{y:,.0f} " + currency,
    ))

    # ── Median forecast line ──
    fig.add_trace(go.Scatter(
        x=dates, y=medians,
        mode="lines+markers",
        name=f"Projected Balance (P50)",
        line=dict(color=highlight_color, width=2.5),
        marker=dict(size=5, color=highlight_color),
        hovertemplate=f"<b>%{{x}}</b><br>Projected: %{{y:,.0f}} {currency}<extra></extra>",
    ))

    # ── Safety threshold ──
    fig.add_hline(
        y=safety_buffer,
        line_dash="dash",
        line_color="#ef4444",
        line_width=1.5,
        annotation_text=f"Safety Buffer: {currency} {safety_buffer:,.0f}",
        annotation_position="top right",
        annotation_font_color="#f87171",
    )

    # ── Shortfall zone shading ──
    if show_shortfall_zone:
        shortfall_dates = [d for d, m in zip(dates, medians) if m < safety_buffer]
        if shortfall_dates:
            fig.add_vrect(
                x0=shortfall_dates[0], x1=shortfall_dates[-1],
                fillcolor="rgba(239,68,68,0.08)",
                layer="below", line_width=0,
                annotation_text="⚠ Potential Shortfall Zone",
                annotation_position="top left",
                annotation_font_color="#f87171",
                annotation_font_size=10,
            )

    # ── Obligations overlay ──
    has_bills = any(b > 0 for b in obligations)
    if has_bills:
        fig.add_trace(go.Bar(
            x=dates, y=obligations,
            name="Scheduled Obligations",
            marker_color="rgba(239,68,68,0.3)",
            yaxis="y2",
            hovertemplate=f"%{{x}}<br>Obligations: %{{y:,.0f}} {currency}<extra></extra>",
        ))

    # ── Current balance marker ──
    fig.add_annotation(
        x=dates[0], y=current_balance,
        text=f"Current: {currency} {current_balance:,.0f}",
        showarrow=True, arrowhead=2, arrowcolor="#10b981",
        font=dict(color="#10b981", size=10),
        ax=20, ay=-30,
    )

    layout_kwargs = dict(
        title=title or f"14-Day Forward Cash-Flow Forecast ({currency})",
        xaxis_title="Date",
        yaxis_title=f"Balance ({currency})",
        hovermode="x unified",
        height=420,
        margin=dict(l=50, r=60, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font_size=11),
        template="plotly_dark",
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_PLOT,
        font=dict(family="Inter, Roboto, sans-serif", color="#e2e8f0", size=12),
        xaxis=dict(gridcolor="#1e3a6e", linecolor="#1e3a6e"),
        yaxis=dict(gridcolor="#1e3a6e", linecolor="#1e3a6e"),
    )

    if has_bills:
        layout_kwargs["yaxis2"] = dict(
            title=f"Obligations ({currency})",
            overlaying="y", side="right",
            showgrid=False, gridcolor="#1e3a6e",
        )

    fig.update_layout(**layout_kwargs)
    return fig
