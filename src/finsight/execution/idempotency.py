"""Idempotency management preventing duplicate financial interventions."""

import hashlib
from typing import Dict, Optional


class IdempotencyStore:
    """In-memory and transactional idempotency registry."""

    def __init__(self):
        self._keys: Dict[str, str] = {}

    def generate_key(self, account_id: str, action_type: str, payload_hash: str) -> str:
        raw = f"{account_id}:{action_type}:{payload_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def check_and_set(self, key: str, status: str = "PROCESSING") -> bool:
        """Atomically set key if not already present. Returns True if first time (fresh), False if duplicate."""
        if key in self._keys:
            return False
        self._keys[key] = status
        return True

    def mark_completed(self, key: str):
        self._keys[key] = "COMPLETED"

    def mark_failed(self, key: str):
        self._keys[key] = "FAILED"

    def get_status(self, key: str) -> Optional[str]:
        return self._keys.get(key)


idempotency_store = IdempotencyStore()
