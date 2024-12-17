"""State management exceptions."""

from typing import Dict, Any, Optional, List
from ..base.exceptions import ServiceError


class StateError(ServiceError):
    """Base class for state management errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize state error.
        
        Args:
            message: Error message
            context: Optional error context
        """
        super().__init__(message)
        self.context = context if context is not None else {}


class StateTransitionError(StateError):
    """Raised when a state transition fails."""
    pass


class InvalidStateError(StateError):
    """Raised when an invalid state is requested."""
    pass


class ConditionError(StateError):
    """Raised when state conditions cannot be evaluated."""
    
    def __init__(self, message: str, failed_conditions: Optional[List[str]] = None):
        """Initialize condition error.
        
        Args:
            message: Error message
            failed_conditions: List of failed condition names
        """
        super().__init__(message)
        self.conditions = {"failed_conditions": failed_conditions} if failed_conditions else {}
