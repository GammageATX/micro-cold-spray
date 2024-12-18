"""Base exceptions for the application."""

from typing import Dict, Any, Optional


class ServiceError(Exception):
    """Base class for service errors."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize service error.
        
        Args:
            message: Error message
            context: Optional error context
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}


class APIError(ServiceError):
    """Base class for API errors."""
    pass


class ValidationError(ServiceError):
    """Raised when validation fails."""
    pass


class ConfigurationError(ServiceError):
    """Raised when configuration is invalid."""
    pass


class CommunicationError(ServiceError):
    """Raised when communication with hardware fails."""
    pass


class DataCollectionError(ServiceError):
    """Raised when data collection fails."""
    pass


class StateError(ServiceError):
    """Raised when state operations fail."""
    pass


class ProcessError(ServiceError):
    """Raised when process operations fail."""
    pass


class MessageError(ServiceError):
    """Raised when messaging operations fail."""
    pass
