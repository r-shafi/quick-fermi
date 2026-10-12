"""Authorization and multi-tenant access control."""

from typing import Dict, List, Optional, Set
from fastapi import HTTPException, status


class UnauthorizedAccountAccessException(HTTPException):
    def __init__(self, user_id: str, account_id: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: User '{user_id}' is not authorized to access account '{account_id}'.",
        )


class AuthorizationManager:
    """Manages role-based and tenancy access controls for accounts and actions."""

    def __init__(self):
        # In prototype: map user_id to set of authorized account_ids
        self._user_accounts: Dict[str, Set[str]] = {
            "user_demo": {"ACC_001_STABLE", "ACC_002_IRREGULAR", "ACC_003_SPIKE", "ACC_004_DELAYED"},
            "user_sme": {"ACC_005_SME"},
            "user_admin": {"*"},  # Wildcard admin
            "anonymous": set(),
        }

    def register_user_account(self, user_id: str, account_id: str):
        self._user_accounts.setdefault(user_id, set()).add(account_id)

    def verify_account_access(self, user_id: str, account_id: str):
        """Strict backend verification that user owns or has access to account_id."""
        authorized_accounts = self._user_accounts.get(user_id, set())
        if "*" in authorized_accounts:
            return True

        if account_id not in authorized_accounts:
            raise UnauthorizedAccountAccessException(user_id, account_id)
        return True


auth_manager = AuthorizationManager()
