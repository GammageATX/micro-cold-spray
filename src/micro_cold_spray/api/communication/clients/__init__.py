"""Hardware communication client components."""

from micro_cold_spray.api.communication.clients.base import CommunicationClient
from micro_cold_spray.api.communication.clients.mock import MockClient
from micro_cold_spray.api.communication.clients.plc import PLCClient
from micro_cold_spray.api.communication.clients.ssh import SSHClient
from micro_cold_spray.api.communication.clients.factory import create_client

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
