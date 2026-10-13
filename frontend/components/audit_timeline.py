"""Audit timeline component — SHA-256 hash-chained event display."""

import streamlit as st
from typing import Any, Dict, List


def render_audit_timeline(events: List[Dict[str, Any]]) -> None:
    """Render a timeline of linked audit events."""
    if not events:
        st.info("No audit events found for the selected filters.")
        return

    for i, event in enumerate(events):
        status = event.get("authorization_result", event.get("status", "unknown")).upper()
        color = {"APPROVED": "#10b981", "REJECTED": "#ef4444", "EXECUTED": "#3b82f6",
                 "PENDING": "#f59e0b", "BLOCKED": "#ef4444"}.get(status, "#64748b")

        audit_hash = event.get("audit_hash", "")
        hash_display = audit_hash[:16] + "…" if len(audit_hash) > 16 else audit_hash
        integrity = event.get("integrity_verified", True)
        integrity_icon = "🔒" if integrity else "⚠️"
        integrity_color = "#10b981" if integrity else "#ef4444"

        st.markdown(
            f"""
            <div style="
                display:flex; align-items:flex-start; gap:12px;
                margin-bottom:8px; padding:12px 16px;
                background:#0f2044; border:1px solid #1e3a6e;
                border-left:3px solid {color}; border-radius:6px;
            ">
                <div style="min-width:50px; text-align:center;">
                    <div style="font-size:1.2rem;">{integrity_icon}</div>
                    <div style="font-size:0.65rem; color:{integrity_color}; font-weight:700;">
                        {"OK" if integrity else "WARN"}
                    </div>
                </div>
                <div style="flex:1;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <span style="font-weight:600; font-size:0.9rem; color:#e2e8f0;">
                            {event.get("action", "Unknown Action")}
                        </span>
                        <span style="font-size:0.75rem; color:#64748b;">
                            {event.get("timestamp", "")[:19].replace("T", " ")}
                        </span>
                    </div>
                    <div style="display:flex; gap:16px; font-size:0.78rem; color:#94a3b8;">
                        <span>Account: <code>{event.get("account_ref", "—")}</code></span>
                        <span>Actor: <code>{event.get("actor", "system")}</code></span>
                        <span style="color:{color}; font-weight:600;">{status}</span>
                    </div>
                    <div style="margin-top:4px; font-size:0.72rem; color:#475569; font-family:'JetBrains Mono', monospace;">
                        Hash: {hash_display}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_linked_timeline(chain: List[Dict[str, Any]]) -> None:
    """Render a linked risk→recommendation→approval→execution chain."""
    if not chain:
        st.info("No linked timeline available. Run a risk assessment first.")
        return

    steps = [
        ("🔍", "Risk Assessment", "risk_assessment"),
        ("💡", "Recommendation", "recommendation"),
        ("✅", "Approval", "approval"),
        ("🚀", "Sandbox Execution", "execution"),
        ("📊", "Observed Outcome", "outcome"),
    ]

    chain_map = {item.get("step_type", item.get("event_type", "")): item for item in chain}

    for icon, label, key in steps:
        item = chain_map.get(key, {})
        has_data = bool(item)
        color = "#3b82f6" if has_data else "#1e3a6e"
        text_color = "#e2e8f0" if has_data else "#475569"
        status_text = item.get("status", "NOT YET RECORDED") if has_data else "NOT YET RECORDED"
        detail = item.get("summary", item.get("action", "")) if has_data else ""

        st.markdown(
            f"""
            <div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:4px;">
                <div style="display:flex;flex-direction:column;align-items:center;">
                    <div style="width:32px;height:32px;border-radius:50%;
                        background:{color};display:flex;align-items:center;
                        justify-content:center;font-size:0.9rem;border:2px solid {color};">
                        {icon}
                    </div>
                    <div style="width:2px;height:20px;background:#1e3a6e;margin:2px 0;"></div>
                </div>
                <div style="padding-top:4px;">
                    <div style="font-weight:600;font-size:0.85rem;color:{text_color};">{label}</div>
                    <div style="font-size:0.75rem;color:#64748b;">{status_text}</div>
                    {f'<div style="font-size:0.72rem;color:#475569;margin-top:2px;">{detail}</div>' if detail else ''}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
