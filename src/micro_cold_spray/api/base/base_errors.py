"""Base error handling module."""

from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import HTTPException, status


# Common status codes
SERVICE_ERROR = status.HTTP_503_SERVICE_UNAVAILABLE
NOT_IMPLEMENTED = status.HTTP_501_NOT_IMPLEMENTED
CONFLICT = status.HTTP_409_CONFLICT
NOT_FOUND = status.HTTP_404_NOT_FOUND
VALIDATION_ERROR = status.HTTP_422_UNPROCESSABLE_ENTITY
BAD_REQUEST = status.HTTP_400_BAD_REQUEST


def create_error(
    message: str,
    status_code: int,  # Required to be explicit about error type
    context: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None
) -> HTTPException:
    """Create HTTP exception with consistent format.
    
    Common status codes:
    - 503 Service Unavailable: Service failed to start/stop
    - 501 Not Implemented: Service methods not implemented
    - 409 Conflict: Service already registered/running
    - 404 Not Found: Service not found
    - 422 Unprocessable Entity: Invalid configuration/data
    - 400 Bad Request: Invalid request parameters
    
    Args:
        message: Error message
        status_code: HTTP status code (required)
        context: Optional error context
        cause: Optional cause exception
        
    Returns:
        HTTPException with formatted detail
    """
    detail = {
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "context": context or {}
    }
    
    if cause:
        detail["context"]["error"] = str(cause)
        
    error = HTTPException(
        status_code=status_code,
        detail=detail
    )
    
    if cause:
        error.__cause__ = cause
        
    return error
