"""Communication service exceptions."""

from typing import Dict, Any
from ..base.exceptions import ServiceError


class HardwareError(ServiceError):
    """Hardware communication errors."""
    def __init__(self, message: str, device: str, context: Dict[str, Any] = None):
        super().__init__(message, context)
        self.device = device


class ConnectionError(HardwareError):
    """Connection-specific errors."""
    pass
