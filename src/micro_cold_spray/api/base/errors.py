"""Error handling utilities."""

from enum import Enum
from typing import Dict, Any, Optional
from fastapi import status


class AppErrorCode(str, Enum):
    """Application-specific error codes.
    
    Maps application-specific errors to appropriate HTTP status codes.
    """
    # Validation Errors (400s)
    VALIDATION_ERROR = "Validation Error"  # 422
    INVALID_STATE = "Invalid State"  # 400
    STATE_TRANSITION_ERROR = "State Transition Error"  # 409
    INVALID_ACTION = "Invalid Action"  # 400
    MISSING_PARAMETER = "Missing Parameter"  # 400
    
    # Service Errors (500s)
    SERVICE_ERROR = "Service Error"  # 500
    CONFIGURATION_ERROR = "Configuration Error"  # 500
    INITIALIZATION_ERROR = "Initialization Error"  # 500
    HARDWARE_ERROR = "Hardware Error"  # 500
    COMMUNICATION_ERROR = "Communication Error"  # 503
    DATA_COLLECTION_ERROR = "Data Collection Error"  # 500
    PROCESS_ERROR = "Process Error"  # 500

    def get_status_code(self) -> int:
        """Get the HTTP status code for this error type."""
        error_status_codes = {
            # Validation Errors
            self.VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
            self.INVALID_STATE: status.HTTP_400_BAD_REQUEST,
            self.STATE_TRANSITION_ERROR: status.HTTP_409_CONFLICT,
            self.INVALID_ACTION: status.HTTP_400_BAD_REQUEST,
            self.MISSING_PARAMETER: status.HTTP_400_BAD_REQUEST,
            
            # Service Errors
            self.SERVICE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            self.CONFIGURATION_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            self.INITIALIZATION_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            self.HARDWARE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            self.COMMUNICATION_ERROR: status.HTTP_503_SERVICE_UNAVAILABLE,
            self.DATA_COLLECTION_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            self.PROCESS_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
        }
        return error_status_codes[self]


def format_error(
    error_code: AppErrorCode,
    message: str,
    extra_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format error response.
    
    Args:
        error_code: Application error code
        message: Error message
        extra_info: Optional additional error context
        
    Returns:
        Formatted error response
    """
    error_response = {
        "code": error_code.name,
        "message": message,
        "detail": f"{error_code.value}: {message}"
    }
    
    if extra_info:
        error_response.update(extra_info)
        
    return error_response
