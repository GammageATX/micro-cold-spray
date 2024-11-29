"""Core exceptions module."""

class CoreError(Exception):
    """Base exception for all core errors."""
    pass

class SystemInitializationError(CoreError):
    """System initialization errors."""
    pass

class ConfigError(CoreError):
    """Configuration related errors."""
    pass

class ConfigurationError(ConfigError):
    """Configuration loading/saving errors."""
    pass

class StateError(CoreError):
    """State management related errors."""
    pass

class MessageBrokerError(CoreError):
    """Message broker related errors."""
    pass

class ValidationError(CoreError):
    """Validation related errors."""
    pass

class OperationError(CoreError):
    """Base class for operation related errors."""
    pass

class ActionError(OperationError):
    """Base class for action related errors."""
    pass

class ActionConfigError(ActionError):
    """Action configuration errors."""
    pass

class ActionExecutionError(ActionError):
    """Action execution errors."""
    pass

class ActionValidationError(ActionError):
    """Action validation errors."""
    pass

class ActionTimeoutError(ActionError):
    """Action timeout errors."""
    pass

class ActionRequirementError(ActionError):
    """Action requirement errors."""
    pass

class ActionParameterError(ActionError):
    """Action parameter errors."""
    pass

class ParameterError(OperationError):
    """Parameter related errors."""
    pass

class PatternError(OperationError):
    """Pattern related errors."""
    pass

class SequenceError(OperationError):
    """Sequence related errors."""
    pass

class HardwareError(CoreError):
    """Base class for hardware related errors."""
    pass

class HardwareConnectionError(HardwareError):
    """Hardware connection related errors."""
    pass

class HardwareCommunicationError(HardwareError):
    """Hardware communication related errors."""
    pass

class HardwareTimeoutError(HardwareError):
    """Hardware timeout related errors."""
    pass

class HardwareStateError(HardwareError):
    """Hardware state related errors."""
    pass

class TagError(HardwareError):
    """Base class for tag related errors."""
    pass

class TagOperationError(TagError):
    """Tag operation related errors."""
    pass

class TagValidationError(TagError):
    """Tag validation related errors."""
    pass

class TagTimeoutError(TagError):
    """Tag timeout related errors."""
    pass

class TagConnectionError(TagError):
    """Tag connection related errors."""
    pass

class UIError(CoreError):
    """UI related errors."""
    pass 