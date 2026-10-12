"""Approval card component for interactive human decision workflow."""

from typing import Any, Callable, Dict
import streamlit as st


def render_approval_card(
    item: Dict[str, Any],
    on_approve: Callable[[str], None],
    on_reject: Callable[[str], None],
):
    """Render an interactive human approval card."""
    app_id = item.get("approval_id")
    title = item.get("title", "Intervention Proposal")
    desc = item.get("description", "")
    action_type = item.get("action_type", "")
    status = item.get("status", "PENDING_APPROVAL")
    changes = item.get("proposed_changes", {})

    status_colors = {
        "PENDING_APPROVAL": "orange",
        "APPROVED": "blue",
        "EXECUTED_IN_SANDBOX": "green",
        "REJECTED": "red",
        "FAILED": "gray",
    }
    badge_color = status_colors.get(status, "gray")

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {title}")
            st.markdown(f"**Action Category:** `{action_type}` | **ID:** `{app_id}`")
        with col2:
            st.markdown(f":{badge_color}[● **{status}**]")

        st.write(desc)

        if changes:
            with st.expander("Inspect Proposed Policy Changes"):
                st.json(changes)

        if status == "PENDING_APPROVAL":
            btn_col1, btn_col2, _ = st.columns([1, 1, 3])
            with btn_col1:
                if st.button("Approve (Sandbox)", key=f"app_{app_id}", type="primary"):
                    on_approve(app_id)
            with btn_col2:
                if st.button("Reject", key=f"rej_{app_id}"):
                    on_reject(app_id)
