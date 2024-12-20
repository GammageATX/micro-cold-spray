"""Base errors module."""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException


def create_error(
    status_code: int,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None
) -> HTTPException:
    """Create error with context.
    
    Args:
        status_code: HTTP status code
        message: Error message
        context: Optional error context
        cause: Optional cause exception
        
    Returns:
        HTTPException with formatted detail
    """
    # Build error detail
    detail = {
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
        
    if context:
        detail["context"] = context
        
    error = HTTPException(status_code=status_code, detail=detail)
    if cause:
        error.__cause__ = cause
    return error
