"""Process service exceptions."""

from typing import Dict, Any
from ..base.exceptions import ServiceError


class ProcessError(ServiceError):
    """Base exception for process operations."""
    def __init__(self, message: str, context: Dict[str, Any] | None = None):
        super().__init__(message, context)
