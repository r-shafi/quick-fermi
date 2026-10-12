"""FastAPI dependencies for database, authentication, authorization, and rate limiting."""

from typing import Generator
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from finsight.database.session import get_db
from finsight.security.authentication import authenticate_request
from finsight.security.authorization import auth_manager
from finsight.security.rate_limits import rate_limiter


def get_current_user(
    x_api_key: str = Depends(authenticate_request),
) -> str:
    """Extract authenticated user_id."""
    return x_api_key


def verify_account_ownership(
    account_id: str,
    user_id: str = Depends(get_current_user),
) -> str:
    """Verify that caller has permission to view/modify target account_id."""
    auth_manager.verify_account_access(user_id=user_id, account_id=account_id)
    return user_id


def enforce_rate_limit(request: Request, user_id: str = Depends(get_current_user)):
    """Enforce token bucket rate limiting per user/client."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_limiter.check_rate_limit(f"{user_id}:{client_ip}")
