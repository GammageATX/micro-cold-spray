"""State management exceptions."""

from typing import Dict, Any, Optional
from ..base.exceptions import ServiceError


class StateError(ServiceError):
    """Base class for state management errors."""
    pass


class StateTransitionError(StateError):
    """Raised when a state transition fails."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize state transition error.
        
        Args:
            message: Error message
            context: Optional error context
        """
        super().__init__(message)
        self.context = context if context is not None else {}


class InvalidStateError(StateError):
    """Raised when an invalid state is requested."""
    pass


class ConditionError(StateError):
    """Raised when state conditions cannot be evaluated."""
    pass
