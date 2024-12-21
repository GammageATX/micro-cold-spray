"""Factory for creating communication clients."""

from typing import Any, Dict, Optional, Type
from fastapi import status

from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.clients.base import CommunicationClient
from micro_cold_spray.api.communication.clients.mock import MockClient
from micro_cold_spray.api.communication.clients.plc import PLCClient
from micro_cold_spray.api.communication.clients.ssh import SSHClient


# Map of client types to client classes
CLIENT_TYPES = {
    "mock": MockClient,
    "plc": PLCClient,
    "ssh": SSHClient
}

# Required config fields for each client type
REQUIRED_CONFIG = {
    "mock": ["hardware"],
    "plc": ["hardware", "hardware.network", "hardware.network.plc"],
    "ssh": ["hardware", "hardware.network", "hardware.network.ssh"]
}


def validate_config(client_type: str, config: Dict[str, Any]) -> None:
    """Validate client configuration.
    
    Args:
        client_type: Type of client to validate
        config: Configuration to validate
        
    Raises:
        HTTPException: If config is invalid
    """
    if client_type not in REQUIRED_CONFIG:
        raise create_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Unknown client type: {client_type}"
        )
        
    # Check required fields
    for field in REQUIRED_CONFIG[client_type]:
        # Handle nested fields
        current = config
        for part in field.split("."):
            if not isinstance(current, dict) or part not in current:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Missing required config field '{field}' for client type '{client_type}'"
                )
            current = current[part]


def create_client(client_type: str, config: Dict[str, Any]) -> CommunicationClient:
    """Create communication client.
    
    Args:
        client_type: Type of client to create
        config: Client configuration
        
    Returns:
        Communication client instance
        
    Raises:
        HTTPException: If client creation fails
    """
    # Validate client type
    if client_type not in CLIENT_TYPES:
        raise create_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Unknown client type: {client_type}"
        )
        
    # Validate config
    validate_config(client_type, config)
    
    try:
        # Create client instance
        client_class = CLIENT_TYPES[client_type]
        client = client_class(config)
        logger.info(f"Created {client_type} client")
        return client
        
    except Exception as e:
        error_msg = f"Failed to create {client_type} client: {str(e)}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg
        )
