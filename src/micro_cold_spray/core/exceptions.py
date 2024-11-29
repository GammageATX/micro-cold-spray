"""Core exceptions module."""

class CoreError(Exception):
    """Base exception for core module."""
    
    def __init__(self, message: str, context: dict = None):
        """Initialize with message and optional context."""
        super().__init__(message)
        self.context = context or {}

class ValidationError(CoreError):
    """Validation related errors."""
    pass

class OperationError(CoreError):
    """Operation related errors (actions, patterns, sequences)."""
    
    def __init__(self, message: str, operation_type: str, context: dict = None):
        """Initialize with operation type."""
        super().__init__(message, context)
        self.operation_type = operation_type

class HardwareError(CoreError):
    """Hardware related errors."""
    
    def __init__(self, message: str, device: str, context: dict = None):
        """Initialize with device info."""
        super().__init__(message, context)
        self.device = device

class ConfigurationError(CoreError):
    """Configuration related errors."""
    pass

class StateError(CoreError):
    """State management related errors."""
    pass

class MessageError(CoreError):
    """Message broker related errors."""
    pass

class UIError(CoreError):
    """UI related errors."""
    pass 