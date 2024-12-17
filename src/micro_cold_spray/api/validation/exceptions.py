"""Validation service exceptions."""

from typing import Dict, Any, Optional
from ..base.exceptions import ServiceError


class ValidationError(ServiceError):
    """Base class for validation errors."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize validation error.
        
        Args:
            message: Error message
            context: Optional error context
        """
        super().__init__(message, context)
        self.message = message
        self.context = context or {}


class ParameterError(ValidationError):
    """Raised when parameter validation fails."""
    pass


class PatternError(ValidationError):
    """Raised when pattern validation fails."""
    pass


class SequenceError(ValidationError):
    """Raised when sequence validation fails."""
    pass


class HardwareError(ValidationError):
    """Raised when hardware validation fails."""
    pass


class RuleError(ValidationError):
    """Raised when validation rules are invalid."""
    pass


class TagError(ValidationError):
    """Raised when tag validation fails."""
    pass
