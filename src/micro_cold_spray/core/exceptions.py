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

class StateError(Exception):
    """Raised when state management operations fail."""
    pass

# Action Exceptions
class ActionError(Exception):
    """Base exception for action errors."""
    pass

class ActionConfigError(ActionError):
    """Error loading or parsing action configuration."""
    pass

class ActionExecutionError(ActionError):
    """Error during action execution."""
    pass

class ActionValidationError(ActionError):
    """Error during action validation."""
    pass

class ActionTimeoutError(ActionError):
    """Action timed out during execution or validation."""
    pass

class ActionRequirementError(ActionError):
    """Action requirements not met."""
    pass

class ActionParameterError(ActionError):
    """Error with action parameters."""
    pass 