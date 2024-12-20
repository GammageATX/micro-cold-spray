"""Base error handling utilities."""

from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status


def create_error(
    message: str,
    status_code: int,
    context: Optional[dict[str, Any]] = None,
    cause: Optional[Exception] = None,
) -> HTTPException:
    """Create an HTTP error with consistent format.
    
    Args:
        message: Error message
        status_code: HTTP status code (use status.HTTP_* constants)
            400: Bad Request - Client errors (invalid input, bad parameters)
            401: Unauthorized - Authentication required
            403: Forbidden - Permission denied
            404: Not Found - Resource doesn't exist
            409: Conflict - Resource state conflict
            422: Unprocessable Entity - Validation errors
            500: Internal Server Error - Unexpected server errors
            503: Service Unavailable - Service not ready/available
        context: Additional error context
        cause: Original exception that caused this error
        
    Returns:
        HTTPException with formatted error details
    """
    error = HTTPException(
        status_code=status_code,
        detail={
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
        },
    )
    if cause:
        error.__cause__ = cause
    return error
