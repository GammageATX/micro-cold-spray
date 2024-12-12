"""Core exceptions module."""


class APIError(Exception):
    """Base exception for core module."""

    def __init__(self, message: str, context: dict | None = None):
        """Initialize with message and optional context."""
        super().__init__(message)
        self.context = context if context is not None else {}


class ValidationError(APIError):
    """Validation related errors."""


class ConfigurationError(APIError):
    """Configuration related errors."""


class OperationError(APIError):
    """Operation related errors (actions, patterns, sequences)."""

    def __init__(
            self,
            message: str,
            operation_type: str,
            context: dict | None = None):
        """Initialize with operation type."""
        super().__init__(message, context)
        self.operation_type = operation_type


class HardwareError(APIError):
    """Hardware related errors."""

    def __init__(self, message: str, device: str, context: dict | None = None):
        """Initialize with device info."""
        super().__init__(message, context)
        self.device = device


class StateError(APIError):
    """State management related errors."""


class ServiceError(APIError):
    """Service related errors."""


class MessageError(APIError):
    """Message broker related errors."""


class DataError(APIError):
    """Data collection and storage related errors."""


class UIError(APIError):
    """UI related errors."""
