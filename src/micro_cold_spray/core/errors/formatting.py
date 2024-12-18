"""Error formatting utilities.

Provides consistent error formatting across the application.
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException

from .codes import AppErrorCode
from .exceptions import ServiceError


def format_error(
    error_code: AppErrorCode,
    message: str,
    extra_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format error response following FastAPI conventions.
    
    Args:
        error_code: Application error code
        message: Error message
        extra_info: Optional additional error context
        
    Returns:
        Formatted error response
    """
    error_response = {
        "detail": {
            "code": error_code.name,
            "message": message
        }
    }
    
    if extra_info:
        error_response["detail"].update(extra_info)
        
    return error_response


def format_service_error(error: ServiceError) -> Dict[str, Any]:
    """Format service error for API response.
    
    Args:
        error: Service error instance
        
    Returns:
        Formatted error response
    """
    return format_error(
        error_code=AppErrorCode.SERVICE_ERROR,
        message=str(error),
        extra_info=error.context
    )


def raise_http_error(
    error_code: AppErrorCode,
    message: str,
    extra_info: Optional[Dict[str, Any]] = None
) -> None:
    """Raise HTTPException with formatted error.
    
    Args:
        error_code: Application error code
        message: Error message
        extra_info: Optional additional error context
        
    Raises:
        HTTPException: With formatted error response
    """
    raise HTTPException(
        status_code=error_code.get_status_code(),
        detail=format_error(error_code, message, extra_info)["detail"]
    )
