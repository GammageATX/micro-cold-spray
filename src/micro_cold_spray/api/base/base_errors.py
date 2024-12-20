"""Base errors module."""

from typing import Dict, Any, Optional
from fastapi import HTTPException


def create_http_error(
    message: str,
    status_code: int,
    context: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None
) -> HTTPException:
    """Create HTTP error with context."""
    detail = message
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        detail = f"{message} ({context_str})"
    
    error = HTTPException(status_code=status_code, detail=detail)
    if cause:
        error.__cause__ = cause
    return error
