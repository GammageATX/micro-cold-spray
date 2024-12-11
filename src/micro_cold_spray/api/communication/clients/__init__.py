"""Hardware communication client components."""

from .base import CommunicationClient
from .plc import PLCClient
from .ssh import SSHClient
from .mock import MockPLCClient, MockSSHClient
from .factory import (
    create_plc_client,
    create_ssh_client,
    create_client,
    PLCClientType,
    SSHClientType
)

__all__ = [
    # Base classes
    'CommunicationClient',
    # Client implementations
    'PLCClient',
    'SSHClient',
    'MockPLCClient',
    'MockSSHClient',
    # Factory functions
    'create_plc_client',
    'create_ssh_client',
    'create_client',
    # Type aliases
    'PLCClientType',
    'SSHClientType'
]
