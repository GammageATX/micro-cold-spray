"""Communication API package."""

from .exceptions import HardwareError, ConnectionError
from .service import CommunicationService
from .router import router, init_router
from .services import (
    PLCTagService,
    FeederTagService,
    FeederService,
    TagCacheService
)

__all__ = [
    # Core components
    "CommunicationService",
    "router",
    "init_router",
    # Services
    "PLCTagService",
    "FeederTagService",
    "FeederService",
    "TagCacheService",
    # Exceptions
    "HardwareError",
    "ConnectionError"
]
