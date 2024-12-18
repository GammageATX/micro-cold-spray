"""Application error codes.

Maps application-specific errors to standard HTTP status codes.
"""

from enum import Enum
from fastapi import status


class AppErrorCode(str, Enum):
    """Application-specific error codes.
    
    Each error code maps to a standard HTTP status code.
    This provides a consistent way to handle errors across the application.
    """
    # Client Errors (400s)
    VALIDATION_ERROR = "Validation Error"  # 422
    INVALID_REQUEST = "Invalid Request"  # 400
    RESOURCE_CONFLICT = "Resource Conflict"  # 409
    RESOURCE_NOT_FOUND = "Resource Not Found"  # 404
    
    # Server Errors (500s)
    SERVICE_ERROR = "Service Error"  # 500
    SERVICE_UNAVAILABLE = "Service Unavailable"  # 503

    def get_status_code(self) -> int:
        """Get the HTTP status code for this error type.
        
        Returns:
            HTTP status code from fastapi.status
        """
        error_status_codes = {
            # Client Errors
            self.VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
            self.INVALID_REQUEST: status.HTTP_400_BAD_REQUEST,
            self.RESOURCE_CONFLICT: status.HTTP_409_CONFLICT,
            self.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
            
            # Server Errors
            self.SERVICE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            self.SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
        }
        return error_status_codes[self]
