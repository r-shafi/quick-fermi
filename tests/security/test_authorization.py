"""Security tests for multi-tenant account isolation, authentication, and rate limiting."""

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from finsight.main import app
from finsight.security.authorization import AuthorizationManager, UnauthorizedAccountAccessException
from finsight.security.rate_limits import TokenBucketRateLimiter

client = TestClient(app)


def test_cross_tenant_isolation_unit():
    auth = AuthorizationManager()

    # user_sme only has access to ACC_005_SME
    assert auth.verify_account_access("user_sme", "ACC_005_SME") is True

    # Accessing personal account ACC_001_STABLE must raise UnauthorizedAccountAccessException
    with pytest.raises(UnauthorizedAccountAccessException):
        auth.verify_account_access("user_sme", "ACC_001_STABLE")

    with pytest.raises(UnauthorizedAccountAccessException):
        auth.verify_account_access("anonymous", "ACC_001_STABLE")


def test_cross_tenant_isolation_api():
    # Attempt to access ACC_005_SME using headers for user_demo
    headers = {"X-User-ID": "user_demo"}
    resp = client.get("/api/v1/accounts/ACC_005_SME/summary", headers=headers)
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_token_bucket_rate_limiter():
    limiter = TokenBucketRateLimiter(capacity=3, refill_rate_per_sec=0.0)

    # First 3 requests allowed
    assert limiter.is_allowed("test_client") is True
    assert limiter.is_allowed("test_client") is True
    assert limiter.is_allowed("test_client") is True

    # 4th request must be denied
    assert limiter.is_allowed("test_client") is False

    with pytest.raises(HTTPException) as exc_info:
        limiter.check_rate_limit("test_client")
    assert exc_info.value.status_code == 429
