"""Hardware client factory."""
from typing import Any, Dict, Union, TypeAlias

from loguru import logger

from .plc_client import PLCClient
from .ssh_client import SSHClient
from .mock_clients import MockPLCClient, MockSSHClient

__all__ = [
    'PLCClientType',
    'SSHClientType',
    'create_plc_client',
    'create_ssh_client'
]

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
        return MockPLCClient(config)
    else:
        logger.info("Creating real PLC client")
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
        return MockSSHClient(config)
    else:
        logger.info("Creating real SSH client")
        return SSHClient(config)
