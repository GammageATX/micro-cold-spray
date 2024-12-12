"""Process service exceptions."""

from typing import Dict, Any, Optional
from ..base.exceptions import ServiceError


class ProcessError(ServiceError):
    """Base class for process errors."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, context)


class SequenceError(ProcessError):
    """Raised when sequence operations fail."""
    pass


class PatternError(ProcessError):
    """Raised when pattern operations fail."""
    pass


class ParameterError(ProcessError):
    """Raised when parameter operations fail."""
    pass


class ActionError(ProcessError):
    """Raised when action execution fails."""
    pass


class ValidationError(ProcessError):
    """Raised when process validation fails."""
    pass


class ExecutionError(ProcessError):
    """Raised when sequence execution fails."""
    pass
