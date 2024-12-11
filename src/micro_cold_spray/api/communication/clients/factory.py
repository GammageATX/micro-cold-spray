"""Hardware client factory."""

from typing import Any, Dict, Union, TypeAlias

from loguru import logger

from .base import CommunicationClient
from .plc import PLCClient
from .ssh import SSHClient
from .mock import MockPLCClient, MockSSHClient

# Type aliases to shorten return type hints
PLCClientType: TypeAlias = Union[PLCClient, MockPLCClient]
SSHClientType: TypeAlias = Union[SSHClient, MockSSHClient]


def create_plc_client(config: Dict[str, Any], use_mock: bool = False) -> PLCClientType:
    """Create PLC client instance.

    Args:
        config: Hardware configuration dictionary
        use_mock: Whether to create a mock client

    Returns:
        PLCClient or MockPLCClient instance
    """
    if use_mock:
        logger.info("Creating mock PLC client")
        return MockPLCClient({})  # Mock client doesn't need config
    else:
        logger.info("Creating real PLC client")
        if not config or 'hardware' not in config:
            raise ValueError("Missing hardware configuration")
        return PLCClient(config)


def create_ssh_client(config: Dict[str, Any], use_mock: bool = False) -> SSHClientType:
    """Create SSH client instance.

    Args:
        config: Hardware configuration dictionary
        use_mock: Whether to create a mock client

    Returns:
        SSHClient or MockSSHClient instance
    """
    if use_mock:
        logger.info("Creating mock SSH client")
        return MockSSHClient({})  # Mock client doesn't need config
    else:
        logger.info("Creating real SSH client")
        if not config or 'hardware' not in config:
            raise ValueError("Missing hardware configuration")
        return SSHClient(config)


def create_client(
    client_type: str,
    config: Dict[str, Any],
    use_mock: bool = False
) -> CommunicationClient:
    """Create a client instance of the specified type.

    Args:
        client_type: Type of client to create ('plc' or 'ssh')
        config: Hardware configuration dictionary
        use_mock: Whether to create a mock client

    Returns:
        Client instance

    Raises:
        ValueError: If client type is invalid
    """
    if client_type == 'plc':
        return create_plc_client(config, use_mock)
    elif client_type == 'ssh':
        return create_ssh_client(config, use_mock)
    else:
        raise ValueError(f"Invalid client type: {client_type}")
