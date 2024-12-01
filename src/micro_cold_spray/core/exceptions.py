"""Core exceptions module."""


class CoreError(Exception):
    """Base exception for core module."""

    def __init__(self, message: str, context: dict | None = None):
        """Initialize with message and optional context."""
        super().__init__(message)
        self.context = context if context is not None else {}


class ValidationError(CoreError):
    """Validation related errors."""


class OperationError(CoreError):
    """Operation related errors (actions, patterns, sequences)."""

    def __init__(
            self,
            message: str,
            operation_type: str,
            context: dict | None = None):
        """Initialize with operation type."""
        super().__init__(message, context)
        self.operation_type = operation_type


class HardwareError(CoreError):
    """Hardware related errors."""

    def __init__(self, message: str, device: str, context: dict | None = None):
        """Initialize with device info."""
        super().__init__(message, context)
        self.device = device


class ConfigurationError(CoreError):
    """Configuration related errors."""


class StateError(CoreError):
    """State management related errors."""


class MessageError(CoreError):
    """Message broker related errors."""


class UIError(CoreError):
    """UI related errors."""
