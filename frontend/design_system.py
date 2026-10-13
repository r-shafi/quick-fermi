"""FinSight AI — Professional FinTech Design System.

Provides CSS injection, color tokens, typography, and shared style helpers
for the competition-grade dashboard.
"""

import streamlit as st


# ─── Color Palette ───────────────────────────────────────────────────────────
COLORS = {
    "bg_primary":    "#0a1628",   # Dark navy — main surface
    "bg_secondary":  "#0f2044",   # Slightly lighter navy — cards
    "bg_tertiary":   "#162d5a",   # Panel / raised surface
    "border":        "#1e3a6e",   # Subtle borders
    "accent_blue":   "#3b82f6",   # Primary action
    "accent_light":  "#60a5fa",   # Hover / secondary
    "success":       "#10b981",   # VERIFIED / PASS
    "warning":       "#f59e0b",   # WARNING / ASSUMPTION
    "danger":        "#ef4444",   # BLOCKED / FAIL / CRITICAL
    "info":          "#8b5cf6",   # INFO / RESEARCH
    "neutral":       "#64748b",   # UNVALIDATED / N/A
    "text_primary":  "#e2e8f0",   # Main body text
    "text_secondary":"#94a3b8",   # Muted text / captions
    "text_accent":   "#93c5fd",   # Links / highlights
    "simulated":     "#f59e0b",   # SIMULATED badge
    "sandbox":       "#8b5cf6",   # SANDBOX badge
}

STATUS_COLORS = {
    "VERIFIED":      COLORS["success"],
    "SIMULATED":     COLORS["simulated"],
    "ASSUMPTION":    COLORS["warning"],
    "UNVALIDATED":   COLORS["neutral"],
    "BLOCKED":       COLORS["danger"],
    "SANDBOX":       COLORS["sandbox"],
    "PENDING":       COLORS["warning"],
    "APPROVED":      COLORS["success"],
    "REJECTED":      COLORS["danger"],
    "EXPIRED":       COLORS["neutral"],
    "PASS":          COLORS["success"],
    "FAIL":          COLORS["danger"],
    "NOT_EVALUATED": COLORS["neutral"],
    "PARTIAL":       COLORS["warning"],
}


def inject_css() -> None:
    """Inject the global dark-mode CSS into the Streamlit app."""
    st.markdown(
        f"""
        <style>
        /* ── Google Fonts ── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        /* ── Root & Background ── */
        html, body, [data-testid="stAppViewContainer"] {{
            background-color: {COLORS["bg_primary"]};
            color: {COLORS["text_primary"]};
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}

        [data-testid="stSidebar"] {{
            background-color: {COLORS["bg_secondary"]};
            border-right: 1px solid {COLORS["border"]};
        }}

        [data-testid="stHeader"] {{
            background-color: transparent;
        }}

        /* ── Typography ── */
        h1 {{ font-size: 1.8rem; font-weight: 700; color: {COLORS["text_primary"]}; letter-spacing: -0.02em; }}
        h2 {{ font-size: 1.4rem; font-weight: 600; color: {COLORS["text_primary"]}; }}
        h3 {{ font-size: 1.1rem; font-weight: 600; color: {COLORS["text_secondary"]}; text-transform: uppercase; letter-spacing: 0.05em; }}
        p, li {{ color: {COLORS["text_secondary"]}; line-height: 1.6; }}
        code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.85em; background: {COLORS["bg_tertiary"]}; padding: 0.1em 0.4em; border-radius: 3px; color: {COLORS["text_accent"]}; }}

        /* ── Metrics ── */
        [data-testid="stMetric"] {{
            background: {COLORS["bg_secondary"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            padding: 16px;
        }}
        [data-testid="stMetricLabel"] {{ color: {COLORS["text_secondary"]}; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
        [data-testid="stMetricValue"] {{ color: {COLORS["text_primary"]}; font-weight: 700; font-size: 1.6rem; }}

        /* ── Buttons ── */
        [data-testid="stButton"] > button {{
            background-color: {COLORS["accent_blue"]};
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.875rem;
            padding: 0.5rem 1rem;
            transition: background-color 0.15s ease;
        }}
        [data-testid="stButton"] > button:hover {{
            background-color: {COLORS["accent_light"]};
        }}

        /* ── Inputs ── */
        [data-testid="stSelectbox"], [data-testid="stTextInput"], [data-testid="stNumberInput"] {{
            background: {COLORS["bg_secondary"]};
            color: {COLORS["text_primary"]};
            border-radius: 6px;
        }}

        /* ── Expander ── */
        [data-testid="stExpander"] {{
            background: {COLORS["bg_secondary"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
        }}

        /* ── Tabs ── */
        [data-testid="stTab"] {{
            background: {COLORS["bg_secondary"]};
            border-radius: 6px 6px 0 0;
        }}

        /* ── Divider ── */
        hr {{ border-color: {COLORS["border"]}; }}

        /* ── DataFrames ── */
        [data-testid="stDataFrame"] {{
            background: {COLORS["bg_secondary"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
        }}

        /* ── Alerts / Info boxes ── */
        [data-testid="stAlert"] {{ border-radius: 8px; }}

        /* ── Sidebar navigation ── */
        [data-testid="stSidebarNav"] a {{
            color: {COLORS["text_secondary"]};
            font-size: 0.875rem;
            font-weight: 500;
        }}
        [data-testid="stSidebarNav"] a:hover {{
            color: {COLORS["text_accent"]};
        }}
        [data-testid="stSidebarNav"] .st-selected {{
            color: {COLORS["text_accent"]};
            font-weight: 600;
        }}

        /* ── Custom card ── */
        .finsight-card {{
            background: {COLORS["bg_secondary"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 12px;
        }}
        .finsight-card-header {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {COLORS["text_secondary"]};
            margin-bottom: 8px;
        }}
        .finsight-card-value {{
            font-size: 1.6rem;
            font-weight: 700;
            color: {COLORS["text_primary"]};
        }}
        .finsight-card-meta {{
            font-size: 0.75rem;
            color: {COLORS["text_secondary"]};
            margin-top: 6px;
        }}

        /* ── Status badges ── */
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}
        .badge-verified   {{ background: #064e3b; color: #34d399; border: 1px solid #065f46; }}
        .badge-simulated  {{ background: #451a03; color: #fbbf24; border: 1px solid #78350f; }}
        .badge-assumption {{ background: #451a03; color: #f59e0b; border: 1px solid #78350f; }}
        .badge-unvalidated{{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
        .badge-blocked    {{ background: #450a0a; color: #f87171; border: 1px solid #7f1d1d; }}
        .badge-sandbox    {{ background: #2e1065; color: #c4b5fd; border: 1px solid #4c1d95; }}
        .badge-pending    {{ background: #451a03; color: #fcd34d; border: 1px solid #78350f; }}
        .badge-pass       {{ background: #064e3b; color: #34d399; border: 1px solid #065f46; }}
        .badge-fail       {{ background: #450a0a; color: #f87171; border: 1px solid #7f1d1d; }}
        .badge-critical   {{ background: #450a0a; color: #fca5a5; border: 1px solid #991b1b; }}
        .badge-high       {{ background: #431407; color: #fb923c; border: 1px solid #7c2d12; }}
        .badge-medium     {{ background: #451a03; color: #fbbf24; border: 1px solid #78350f; }}
        .badge-low        {{ background: #1e3a5f; color: #60a5fa; border: 1px solid #1e40af; }}

        /* ── Competition banner ── */
        .competition-banner {{
            background: linear-gradient(135deg, #1e3a8a 0%, #312e81 50%, #1e1b4b 100%);
            border: 1px solid #3730a3;
            border-radius: 10px;
            padding: 12px 20px;
            margin-bottom: 16px;
            text-align: center;
        }}
        .competition-banner h4 {{
            color: #c7d2fe;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin: 0;
        }}
        .competition-banner p {{
            color: #a5b4fc;
            font-size: 0.85rem;
            margin: 4px 0 0;
        }}

        /* ── Evidence panel ── */
        .evidence-panel {{
            background: {COLORS["bg_tertiary"]};
            border-left: 3px solid {COLORS["accent_blue"]};
            padding: 12px 16px;
            border-radius: 0 6px 6px 0;
            margin: 8px 0;
        }}
        .evidence-panel .evidence-source {{
            font-size: 0.75rem;
            color: {COLORS["text_accent"]};
            font-weight: 600;
        }}
        .evidence-panel .evidence-text {{
            font-size: 0.85rem;
            color: {COLORS["text_secondary"]};
            margin-top: 4px;
        }}

        /* ── Limitation disclaimer ── */
        .limitation-box {{
            background: #1c1917;
            border: 1px solid #57534e;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 0.8rem;
            color: #a8a29e;
        }}
        .limitation-box::before {{
            content: "⚠ LIMITATION: ";
            color: #fbbf24;
            font-weight: 700;
        }}

        /* ── Sandbox label ── */
        .sandbox-label {{
            background: #2e1065;
            color: #c4b5fd;
            border: 1px solid #6d28d9;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            text-align: center;
            letter-spacing: 0.05em;
        }}
        .sandbox-label::before {{ content: "🔬 SANDBOX — "; }}

        /* ── Workflow trace ── */
        .workflow-node {{
            background: {COLORS["bg_secondary"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 8px;
            padding: 12px 16px;
            margin: 6px 0;
            position: relative;
        }}
        .workflow-node.completed {{ border-left: 3px solid {COLORS["success"]}; }}
        .workflow-node.pending   {{ border-left: 3px solid {COLORS["warning"]}; }}
        .workflow-node.error     {{ border-left: 3px solid {COLORS["danger"]}; }}
        .workflow-node .node-name {{ font-weight: 600; font-size: 0.9rem; color: {COLORS["text_primary"]}; }}
        .workflow-node .node-time {{ font-size: 0.75rem; color: {COLORS["text_secondary"]}; }}
        .workflow-node .node-output {{ font-size: 0.8rem; color: {COLORS["text_secondary"]}; margin-top: 4px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value: str, source: str = "", limitation: str = "", delta: str = "") -> str:
    """Return HTML for a financial KPI card."""
    delta_html = f'<div class="finsight-card-delta" style="font-size:0.8rem;color:#34d399;margin-top:2px;">{delta}</div>' if delta else ""
    limitation_html = f'<div style="font-size:0.7rem;color:#78716c;margin-top:6px;">⚠ {limitation}</div>' if limitation else ""
    source_html = f'<div class="finsight-card-meta">Source: {source}</div>' if source else ""
    return f"""
    <div class="finsight-card">
        <div class="finsight-card-header">{label}</div>
        <div class="finsight-card-value">{value}</div>
        {delta_html}{source_html}{limitation_html}
    </div>
    """


def status_badge(status: str) -> str:
    """Return HTML badge for a status string."""
    css_map = {
        "VERIFIED": "badge-verified",
        "SIMULATED": "badge-simulated",
        "ASSUMPTION": "badge-assumption",
        "UNVALIDATED": "badge-unvalidated",
        "BLOCKED": "badge-blocked",
        "SANDBOX": "badge-sandbox",
        "PENDING": "badge-pending",
        "APPROVED": "badge-pass",
        "REJECTED": "badge-fail",
        "EXPIRED": "badge-unvalidated",
        "PASS": "badge-pass",
        "FAIL": "badge-fail",
        "CRITICAL": "badge-critical",
        "HIGH": "badge-high",
        "MEDIUM": "badge-medium",
        "LOW": "badge-low",
    }
    css = css_map.get(status.upper(), "badge-unvalidated")
    return f'<span class="badge {css}">{status}</span>'


def page_header(title: str, subtitle: str = "", badge: str = "") -> None:
    """Render a consistent page header with optional subtitle and status badge."""
    badge_html = status_badge(badge) if badge else ""
    st.markdown(
        f"""
        <div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #1e3a6e;">
            <h1 style="margin-bottom: 4px; display:flex; align-items:center; gap:12px;">
                {title} {badge_html}
            </h1>
            <p style="margin: 0; color: #94a3b8; font-size: 0.9rem;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, badge: str = "") -> None:
    """Render a section header with optional status badge."""
    badge_html = status_badge(badge) if badge else ""
    st.markdown(
        f"<h3 style='margin-top:24px;margin-bottom:12px;'>{title} {badge_html}</h3>",
        unsafe_allow_html=True,
    )


def evidence_panel(source: str, text: str) -> None:
    """Render an evidence panel with source attribution."""
    st.markdown(
        f"""
        <div class="evidence-panel">
            <div class="evidence-source">📎 Evidence: {source}</div>
            <div class="evidence-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def limitation_note(text: str) -> None:
    """Render a prominent limitation disclaimer."""
    st.markdown(f'<div class="limitation-box">{text}</div>', unsafe_allow_html=True)


def sandbox_notice() -> None:
    """Render a prominent SANDBOX execution notice."""
    st.markdown(
        '<div class="sandbox-label">No real transactions are executed. All actions run in simulation mode only.</div>',
        unsafe_allow_html=True,
    )


def competition_banner() -> None:
    """Render the FinTechathon competition context banner."""
    st.markdown(
        """
        <div class="competition-banner">
            <h4>🏆 2026 Shenzhen International FinTech Competition — FinTechathon</h4>
            <p>International Track · Topic E: SME Finance Copilot</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def workflow_node(name: str, status: str, duration_ms: float = 0, output: str = "") -> None:
    """Render a workflow execution node."""
    status_icon = {"completed": "✅", "pending": "⏳", "error": "❌", "skipped": "⏭"}.get(status, "●")
    duration_str = f"{duration_ms:.1f}ms" if duration_ms > 0 else ""
    st.markdown(
        f"""
        <div class="workflow-node {status}">
            <div class="node-name">{status_icon} {name}</div>
            {f'<div class="node-time">{duration_str}</div>' if duration_str else ""}
            {f'<div class="node-output">{output}</div>' if output else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
