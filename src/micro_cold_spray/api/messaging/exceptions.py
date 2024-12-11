"""Messaging service exceptions."""

from typing import Dict, Any
from ..base.exceptions import ServiceError


class MessagingError(ServiceError):
    """Raised when messaging operations fail."""
    def __init__(self, message: str, context: Dict[str, Any] | None = None):
        super().__init__(message, context)
