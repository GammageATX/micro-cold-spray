"""Validation service exceptions."""

from typing import Dict, Any
from ..base.exceptions import ServiceError


class ValidationError(ServiceError):
    """Raised when validation fails."""
    
    def __init__(self, message: str, context: Dict[str, Any] | None = None):
        """Initialize validation error.
        
        Args:
            message: Error message
            context: Optional error context
        """
        super().__init__(message, context)
