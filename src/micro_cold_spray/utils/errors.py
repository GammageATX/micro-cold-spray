"""Error utilities."""

from typing import Optional, Dict, Any
from fastapi import HTTPException


def create_error(
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Create an HTTP error response.
    
    Args:
        status_code: HTTP status code
        message: Error message
        details: Optional error details
        
    Returns:
        HTTPException with error details
    """
    error_content = {
        "status": "error",
        "message": message
    }
    if details:
        error_content["details"] = details
        
    return HTTPException(
        status_code=status_code,
        detail=error_content
    )
