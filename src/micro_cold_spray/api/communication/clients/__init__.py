"""Hardware communication client components."""

from .base import CommunicationClient
from .mock import MockClient
from .plc import PLCClient
from .ssh import SSHClient
from .factory import create_client

__all__ = [
    # Base class
    'CommunicationClient',
    # Client implementations
    'MockClient',
    'PLCClient',
    'SSHClient',
    # Factory function
    'create_client'
]
