"""Application exceptions.

Defines domain-specific exceptions for the application.
These exceptions are used to provide more context about errors
and are typically converted to HTTP responses by the API layer.
"""

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


class HardwareError(CommunicationError):
    """Raised when hardware operations fail.
    
    Used for all hardware-related errors including:
    - Equipment errors
    - Motion errors
    - Sensor errors
    - Control errors
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


class StorageError(DataCollectionError):
    """Raised when storage operations fail.
    
    Used for all storage-related errors including:
    - Database connection errors
    - Query errors
    - Data validation errors
    - Schema errors
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


class ProcessNotFoundError(ProcessError):
    """Error raised when process is not found."""

    def __init__(self, process_id: str):
        """Initialize process not found error.
        
        Args:
            process_id: Process identifier
        """
        super().__init__(
            f"Process {process_id} not found",
            {"process_id": process_id}
        )


class ProcessStateError(ProcessError):
    """Error raised when process state is invalid."""

    def __init__(self, process_id: str, current_state: str, requested_action: str):
        """Initialize process state error.
        
        Args:
            process_id: Process identifier
            current_state: Current process state
            requested_action: Requested process action
        """
        super().__init__(
            f"Invalid process state transition from {current_state} with action {requested_action}",
            {
                "process_id": process_id,
                "current_state": current_state,
                "requested_action": requested_action
            }
        )


class MessageError(ServiceError):
    """Raised when messaging operations fail.
    
    Used for all messaging-related errors including:
    - Queue errors
    - Topic errors
    - Subscription errors
    """
    pass
