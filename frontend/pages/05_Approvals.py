"""Approvals Page: Human-in-the-loop decision queue and audit log."""

import streamlit as st
from api_client import FinsightAPIClient
from components.approval_card import render_approval_card

st.header("📋 Human Approval Queue & Audit Trail")

client: FinsightAPIClient = st.session_state.get("api_client", FinsightAPIClient())
account_id = st.session_state.get("selected_account_id", "ACC_001_STABLE")

try:
    pending_items = client.list_pending_approvals(account_id=account_id)
except Exception as e:
    st.error(f"Failed to fetch approval queue: {e}")
    pending_items = []

def on_approve(app_id: str):
    try:
        res = client.approve_intervention(app_id)
        st.success(f"Intervention {app_id} approved and executed in sandbox! Message: {res.get('message')}")
        st.rerun()
    except Exception as e:
        st.error(f"Approval failed: {e}")

def on_reject(app_id: str):
    try:
        res = client.reject_intervention(app_id)
        st.info(f"Intervention {app_id} rejected.")
        st.rerun()
    except Exception as e:
        st.error(f"Rejection failed: {e}")

st.subheader(f"Pending Approvals for Account `{account_id}` ({len(pending_items)})")

if not pending_items:
    st.success("No pending actions awaiting approval for this account.")
else:
    for item in pending_items:
        render_approval_card(
            item=item,
            on_approve=on_approve,
            on_reject=on_reject,
        )

st.markdown("---")
st.subheader("🔒 Security & Audit Logging Principles")
st.markdown("""
- **Backend Authorization Enforcement:** Every decision is cryptographically logged and authenticated on the backend.
- **Idempotency Guarantee:** Duplicate approvals cannot trigger duplicate action dispatches.
- **Append-Only Auditing:** Every proposal, decision, actor, and status change is immutably recorded.
""")
