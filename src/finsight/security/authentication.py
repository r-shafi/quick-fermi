"""Authentication handler supporting API keys and demo tokens."""

from typing import Optional
from fastapi import Header, HTTPException, status
from finsight.config import settings


def authenticate_request(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """Authenticate incoming HTTP request and return the caller's user_id.
    
    Accepts valid API key or Bearer token; defaults to 'user_demo' for local prototyping.
    """
    # If API key provided
    if x_api_key:
        if x_api_key == "demo-api-key-finsight":
            return "user_demo"
        if x_api_key == "admin-api-key-finsight":
            return "user_admin"
        if x_api_key == "sme-api-key-finsight":
            return "user_sme"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-API-Key provided.",
        )

    # If Bearer token provided
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        if token in ("demo-token", "token-user_demo"):
            return "user_demo"
        if token == "token-user_sme":
            return "user_sme"
        if token == "token-admin":
            return "user_admin"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Bearer token provided.",
        )

    # In local development, fallback gracefully to user_demo if unauthenticated
    if settings.environment == "development":
        return "user_demo"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials missing.",
    )
