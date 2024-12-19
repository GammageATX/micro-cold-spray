"""Base exceptions for the application."""

from typing import Optional, Dict, Any


class ServiceError(Exception):
    """Base exception for service errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize service error.
        
        Args:
            message: Error message
            context: Additional error context
        """
        super().__init__(message)
        self.context = context


class ConfigError(ServiceError):
    """Exception for configuration errors."""
    pass


class ValidationError(ServiceError):
    """Exception for validation errors."""
    pass


class CommunicationError(ServiceError):
    """Exception for communication errors."""
    pass


class ProcessError(ServiceError):
    """Exception for process errors."""
    pass


class DataError(ServiceError):
    """Exception for data errors."""
    pass
