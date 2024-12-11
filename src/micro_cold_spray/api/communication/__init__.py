"""Hardware communication API package."""

from typing import Dict, Any

# Core components
from .router import router, init_router


# Service components
from .services import (
    PLCTagService,
    FeederTagService,
    TagCacheService,
    TagMappingService,
    ValidationError
)


# Client components
from .clients import (
    PLCClient,
    SSHClient,
    MockPLCClient,
    MockSSHClient,
    create_plc_client,
    create_ssh_client,
    PLCClientType,
    SSHClientType
)


# Error types
class HardwareError(Exception):
    """Base exception for hardware communication errors."""
    def __init__(self, message: str, device: str, context: Dict[str, Any] = None):
        super().__init__(message)
        self.device = device
        self.context = context or {}


__all__ = [
    # Router
    'router',
    'init_router',
    # Errors
    'HardwareError',
    # Services
    'PLCTagService',
    'FeederTagService',
    'TagCacheService',
    'TagMappingService',
    'ValidationError',
    # Clients
    'PLCClient',
    'SSHClient',
    'MockPLCClient',
    'MockSSHClient',
    'create_plc_client',
    'create_ssh_client',
    'PLCClientType',
    'SSHClientType'
]
