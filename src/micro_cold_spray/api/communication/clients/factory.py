"""Hardware client factory."""

from typing import Any, Dict, Union, TypeAlias

from loguru import logger

from .base import CommunicationClient
from .plc import PLCClient
from .ssh import SSHClient
from .mock import MockPLCClient, MockSSHClient
from ...base.exceptions import ValidationError

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
        
    Raises:
        ValidationError: If configuration is invalid
    """
    if use_mock:
        logger.info("Creating mock PLC client")
        return MockPLCClient({})
        
    logger.debug(f"Creating real PLC client with config: {config}")
    
    if not config:
        raise ValidationError(
            "Missing hardware configuration",
            {"client": "plc"}
        )
        
    required_fields = ["ip", "tag_file", "polling_interval"]
    missing_fields = [field for field in required_fields if field not in config]
    
    if missing_fields:
        raise ValidationError(
            f"Missing required PLC config fields: {missing_fields}",
            {"client": "plc", "missing_fields": missing_fields}
        )
        
    return PLCClient(config)


def create_ssh_client(config: Dict[str, Any], use_mock: bool = False) -> SSHClientType:
    """Create SSH client instance.
    
    Args:
        config: Hardware configuration dictionary
        use_mock: Whether to create a mock client
        
    Returns:
        SSHClient or MockSSHClient instance
        
    Raises:
        ValidationError: If configuration is invalid
    """
    if use_mock:
        logger.info("Creating mock SSH client")
        return MockSSHClient({})  # Mock client doesn't need config
        
    logger.debug(f"Creating real SSH client with config: {config}")
    
    if not config:
        raise ValidationError(
            "Missing hardware configuration",
            {"client": "ssh"}
        )
        
    required_fields = ["host", "username"]
    missing_fields = [field for field in required_fields if field not in config]
    
    if missing_fields:
        raise ValidationError(
            f"Missing required SSH config fields: {missing_fields}",
            {"client": "ssh", "missing_fields": missing_fields}
        )
        
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
        ValidationError: If client type is invalid
    """
    if client_type == 'plc':
        return create_plc_client(config, use_mock)
    elif client_type == 'ssh':
        return create_ssh_client(config, use_mock)
    else:
        raise ValidationError(
            f"Invalid client type: {client_type}",
            {"client_type": client_type, "valid_types": ["plc", "ssh"]}
        )
