"""Error handling for base module."""

from enum import Enum
from typing import Optional, Any, Dict

from fastapi import status


class AppErrorCode(str, Enum):
    """Application error codes."""
    
    # Service errors
    SERVICE_ERROR = "SERVICE_ERROR"
    SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND"
    SERVICE_START_ERROR = "SERVICE_START_ERROR"
    SERVICE_STOP_ERROR = "SERVICE_STOP_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_NOT_RUNNING = "SERVICE_NOT_RUNNING"
    SERVICE_ALREADY_RUNNING = "SERVICE_ALREADY_RUNNING"
    
    # Configuration errors
    CONFIG_ERROR = "CONFIG_ERROR"
    CONFIG_VALIDATION_ERROR = "CONFIG_VALIDATION_ERROR"
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    CONFIG_INVALID = "CONFIG_INVALID"
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    
    # Runtime errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    
    # Application errors
    APP_ERROR = "APP_ERROR"
    APP_NOT_READY = "APP_NOT_READY"
    APP_STARTUP_ERROR = "APP_STARTUP_ERROR"
    APP_SHUTDOWN_ERROR = "APP_SHUTDOWN_ERROR"


class BaseError(Exception):
    """Base exception class for all application errors."""
    
    def __init__(
        self,
        message: str,
        error_code: AppErrorCode,
        context: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        """Initialize base error.
        
        Args:
            message: Error message
            error_code: Error code
            context: Additional error context
            status_code: HTTP status code
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        self.status_code = status_code

    def __str__(self) -> str:
        """Get string representation.

        Returns:
            Error message
        """
        return self.message

    def to_dict(self) -> dict:
        """Convert error to dictionary.

        Returns:
            Error dictionary
        """
        return {
            "detail": self.message,
            "code": self.error_code,
            "status_code": self.status_code,
            "context": self.context
        }


class ServiceError(BaseError):
    """Base service error."""

    def __init__(
        self,
        message: str,
        error_code: AppErrorCode = AppErrorCode.SERVICE_ERROR,
        status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize service error.

        Args:
            message: Error message
            error_code: Error code
            status_code: HTTP status code
            context: Additional error context
        """
        super().__init__(message, error_code, context, status_code)


class ConfigError(BaseError):
    """Configuration error."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize config error.

        Args:
            message: Error message
            context: Additional error context
        """
        super().__init__(
            message,
            error_code=AppErrorCode.CONFIG_ERROR,
            context=context,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class ValidationError(BaseError):
    """Validation error."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            context: Additional error context
        """
        super().__init__(
            message,
            error_code=AppErrorCode.VALIDATION_ERROR,
            context=context,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


def format_error(
    error_code: AppErrorCode,
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Format error response.
    
    Args:
        error_code: Error code
        message: Error message
        context: Additional error context
        
    Returns:
        Formatted error response
    """
    return {
        "error": {
            "code": error_code,
            "message": message,
            "context": context or {}
        }
    }
