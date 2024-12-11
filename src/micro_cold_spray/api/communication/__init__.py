"""Communication API package."""

from .exceptions import HardwareError, ConnectionError
from .service import CommunicationService
from .router import router, init_router

__all__ = [
    # Core components
    "CommunicationService",
    "router",
    "init_router",
    # Exceptions
    "HardwareError",
    "ConnectionError"
]
