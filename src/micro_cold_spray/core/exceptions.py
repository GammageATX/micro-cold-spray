class SystemInitializationError(Exception):
    """Raised when system initialization fails."""
    pass

class ComponentShutdownError(Exception):
    """Raised when component shutdown fails."""
    pass

class HardwareConnectionError(Exception):
    """Raised when hardware connection fails."""
    pass

class TagOperationError(Exception):
    """Raised when a tag operation fails."""
    pass

class ConfigurationError(Exception):
    """Raised when configuration operations fail."""
    pass

class MonitorError(Exception):
    """Raised when monitor operations fail."""
    pass

class OperationError(Exception):
    """Raised when operation management fails."""
    pass

class ValidationError(Exception):
    """Raised when validation operations fail."""
    pass

class UIError(Exception):
    """Raised when UI operations fail."""
    pass

class MessageBrokerError(Exception):
    """Raised when message broker operations fail."""
    pass 