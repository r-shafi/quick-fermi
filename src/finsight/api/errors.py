"""Standardized error models and global exception handlers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: dict = {}


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": str(exc),
            "details": {"path": request.url.path},
        },
    )


async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": "BAD_REQUEST",
            "message": str(exc),
            "details": {"path": request.url.path},
        },
    )


async def key_error_handler(request: Request, exc: KeyError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error_code": "NOT_FOUND",
            "message": str(exc),
            "details": {"path": request.url.path},
        },
    )
