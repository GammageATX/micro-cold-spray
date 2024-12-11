"""Configuration service exceptions."""

from typing import Dict, Any
from ..base.exceptions import ServiceError


class ConfigurationError(ServiceError):
    """Raised when configuration operations fail."""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        super().__init__(message, context)
