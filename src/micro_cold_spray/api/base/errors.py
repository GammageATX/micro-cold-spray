"""Base error formats and messages."""

from enum import Enum
from typing import Dict, Any, Optional
from fastapi import status


class ErrorCode(str, Enum):
    """Standard HTTP error codes and messages.
    
    Maps standard HTTP status codes to their canonical error messages.
    Used for consistent error handling across all APIs.
    """
    # 4xx Client Errors
    BAD_REQUEST = "Bad Request"
    UNAUTHORIZED = "Unauthorized"
    FORBIDDEN = "Forbidden"
    NOT_FOUND = "Not Found"
    METHOD_NOT_ALLOWED = "Method Not Allowed"
    NOT_ACCEPTABLE = "Not Acceptable"
    REQUEST_TIMEOUT = "Request Timeout"
    CONFLICT = "Conflict"
    GONE = "Gone"
    LENGTH_REQUIRED = "Length Required"
    PRECONDITION_FAILED = "Precondition Failed"
    REQUEST_ENTITY_TOO_LARGE = "Request Entity Too Large"
    REQUEST_URI_TOO_LONG = "Request URI Too Long"
    UNSUPPORTED_MEDIA_TYPE = "Unsupported Media Type"
    REQUESTED_RANGE_NOT_SATISFIABLE = "Requested Range Not Satisfiable"
    EXPECTATION_FAILED = "Expectation Failed"
    UNPROCESSABLE_ENTITY = "Unprocessable Entity"
    TOO_MANY_REQUESTS = "Too Many Requests"

    # 5xx Server Errors
    INTERNAL_ERROR = "Internal Server Error"
    NOT_IMPLEMENTED = "Not Implemented"
    BAD_GATEWAY = "Bad Gateway"
    SERVICE_UNAVAILABLE = "Service Unavailable"
    GATEWAY_TIMEOUT = "Gateway Timeout"
    HTTP_VERSION_NOT_SUPPORTED = "HTTP Version Not Supported"
    HEALTH_CHECK_ERROR = "Health Check Failed"

    # Common Application-Specific Errors (mapped to appropriate HTTP codes)
    VALIDATION_ERROR = "Validation Error"
    INVALID_STATE = "Invalid State"
    STATE_TRANSITION_ERROR = "State Transition Error"
    CONDITION_ERROR = "Condition Error"
    DATABASE_ERROR = "Database Error"
    CONFIGURATION_ERROR = "Configuration Error"
    INITIALIZATION_ERROR = "Initialization Error"
    HARDWARE_ERROR = "Hardware Error"
    COMMUNICATION_ERROR = "Communication Error"
    INVALID_ACTION = "Invalid Action"
    MISSING_PARAMETER = "Missing Parameter"

    def get_status_code(self) -> int:
        """Get the HTTP status code for this error type."""
        error_status_codes = {
            # 4xx Client Errors
            self.BAD_REQUEST: status.HTTP_400_BAD_REQUEST,
            self.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
            self.FORBIDDEN: status.HTTP_403_FORBIDDEN,
            self.NOT_FOUND: status.HTTP_404_NOT_FOUND,
            self.METHOD_NOT_ALLOWED: status.HTTP_405_METHOD_NOT_ALLOWED,
            self.NOT_ACCEPTABLE: status.HTTP_406_NOT_ACCEPTABLE,
            self.REQUEST_TIMEOUT: status.HTTP_408_REQUEST_TIMEOUT,
            self.CONFLICT: status.HTTP_409_CONFLICT,
            self.GONE: status.HTTP_410_GONE,
            self.LENGTH_REQUIRED: status.HTTP_411_LENGTH_REQUIRED,
            self.PRECONDITION_FAILED: status.HTTP_412_PRECONDITION_FAILED,
            self.REQUEST_ENTITY_TOO_LARGE: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            self.REQUEST_URI_TOO_LONG: status.HTTP_414_REQUEST_URI_TOO_LONG,
            self.UNSUPPORTED_MEDIA_TYPE: status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            self.REQUESTED_RANGE_NOT_SATISFIABLE: status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            self.EXPECTATION_FAILED: status.HTTP_417_EXPECTATION_FAILED,
            self.UNPROCESSABLE_ENTITY: status.HTTP_422_UNPROCESSABLE_ENTITY,
            self.TOO_MANY_REQUESTS: status.HTTP_429_TOO_MANY_REQUESTS,

            # 5xx Server Errors
            self.INTERNAL_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            self.NOT_IMPLEMENTED: status.HTTP_501_NOT_IMPLEMENTED,
            self.BAD_GATEWAY: status.HTTP_502_BAD_GATEWAY,
            self.SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
            self.GATEWAY_TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
            self.HTTP_VERSION_NOT_SUPPORTED: status.HTTP_505_HTTP_VERSION_NOT_SUPPORTED,
            self.HEALTH_CHECK_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,

            # Application-Specific Errors
            self.VALIDATION_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
            self.INVALID_STATE: status.HTTP_400_BAD_REQUEST,
            self.STATE_TRANSITION_ERROR: status.HTTP_409_CONFLICT,
            self.CONDITION_ERROR: status.HTTP_412_PRECONDITION_FAILED,
            self.DATABASE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            self.CONFIGURATION_ERROR: status.HTTP_400_BAD_REQUEST,
            self.INITIALIZATION_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            self.HARDWARE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
            self.COMMUNICATION_ERROR: status.HTTP_503_SERVICE_UNAVAILABLE,
            self.INVALID_ACTION: status.HTTP_400_BAD_REQUEST,
            self.MISSING_PARAMETER: status.HTTP_400_BAD_REQUEST,
        }
        return error_status_codes[self]


def format_error(code: ErrorCode, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format error response.
    
    Args:
        code: Error code from ErrorCode enum
        message: Detailed error message
        data: Optional additional error data/context
        
    Returns:
        Formatted error response with standard structure:
        {
            "detail": {
                "error": "<error_type>",
                "message": "Detailed error message",
                "data": { ...additional data if provided }
            }
        }
    """
    error_response = {
        "detail": {
            "error": code.value,
            "message": message
        }
    }
    
    if data:
        error_response["detail"]["data"] = data
    
    return error_response
