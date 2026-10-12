"""Secrets manager ensuring credentials are loaded from environment only."""

import os
from typing import Optional


class SecretsManager:
    """Safely retrieves credentials without hardcoding or logging."""

    @staticmethod
    def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(key, default)

    @staticmethod
    def require_secret(key: str) -> str:
        val = os.getenv(key)
        if not val:
            raise KeyError(f"Required secret environment variable '{key}' is not set.")
        return val


secrets_manager = SecretsManager()
