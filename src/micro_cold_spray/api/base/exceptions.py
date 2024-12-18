"""Base exceptions for the application."""

from typing import Dict, Any, Optional


class ServiceError(Exception):
    """Base class for service errors.
    
    All service-specific exceptions should inherit from this class.
    The error context can be used to provide additional information
    that will be included in the error response.
    """
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize service error.
        
        Args:
            message: Error message
            context: Optional error context
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}


class ValidationError(ServiceError):
    """Raised when validation fails.
    
    Used for all validation-related errors including:
    - Data validation
    - Schema validation
    - Format validation
    - Rule validation
    """
    pass


class ConfigurationError(ServiceError):
    """Raised when configuration is invalid.
    
    Used for all configuration-related errors including:
    - Invalid config format
    - Missing required config
    - Config loading errors
    """
    pass


class CommunicationError(ServiceError):
    """Raised when communication with hardware fails.
    
    Used for all communication-related errors including:
    - Connection failures
    - Protocol errors
    - Timeout errors
    """
    pass


class DataCollectionError(ServiceError):
    """Raised when data collection fails.
    
    Used for all data collection errors including:
    - Storage errors
    - Sampling errors
    - Buffer errors
    """
    pass


class StateError(ServiceError):
    """Raised when state operations fail.
    
    Used for all state-related errors including:
    - Invalid state transitions
    - State conflicts
    - State persistence errors
    """
    pass


class ProcessError(ServiceError):
    """Raised when process operations fail.
    
    Used for all process-related errors including:
    - Sequence errors
    - Action errors
    - Resource errors
    """
    pass


class MessageError(ServiceError):
    """Raised when messaging operations fail.
    
    Used for all messaging-related errors including:
    - Queue errors
    - Topic errors
    - Subscription errors
    """
    pass
