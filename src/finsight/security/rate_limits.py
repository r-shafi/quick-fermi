"""Rate limiting and token-bucket protection against abuse."""

import time
from typing import Dict, Tuple
from fastapi import HTTPException, status


class TokenBucketRateLimiter:
    """In-memory token bucket rate limiter per client IP or user."""

    def __init__(self, capacity: int = 120, refill_rate_per_sec: float = 2.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self.buckets: Dict[str, Tuple[float, float]] = {}  # key -> (tokens, last_update)

    def is_allowed(self, client_key: str, cost: float = 1.0) -> bool:
        now = time.time()
        if client_key not in self.buckets:
            self.buckets[client_key] = (float(self.capacity) - cost, now)
            return True

        tokens, last_update = self.buckets[client_key]
        # Refill
        elapsed = now - last_update
        tokens = min(float(self.capacity), tokens + elapsed * self.refill_rate)

        if tokens >= cost:
            self.buckets[client_key] = (tokens - cost, now)
            return True
        else:
            self.buckets[client_key] = (tokens, now)
            return False

    def check_rate_limit(self, client_key: str):
        if not self.is_allowed(client_key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down requests.",
            )


rate_limiter = TokenBucketRateLimiter(capacity=120, refill_rate_per_sec=2.0)
