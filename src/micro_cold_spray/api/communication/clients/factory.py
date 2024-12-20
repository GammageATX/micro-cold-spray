"""Factory functions for creating hardware communication clients."""

from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.clients.base import CommunicationClient
from micro_cold_spray.api.communication.clients.mock import MockClient
from micro_cold_spray.api.communication.clients.plc import PLCClient


def create_client(client_type: str, config: Dict[str, Any]) -> CommunicationClient:
    """Create a hardware communication client.
    
    Args:
        client_type: Type of client to create ('mock', 'plc')
        config: Client configuration
        
    Returns:
        Initialized client instance
        
    Raises:
        HTTPException: If client type is invalid or initialization fails
    """
    try:
        if client_type == "mock":
            return MockClient(config)
        elif client_type == "plc":
            return PLCClient(config)
        else:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Invalid client type: {client_type}",
                context={"type": client_type}
            )
    except Exception as e:
        logger.error(f"Failed to create {client_type} client: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to create {client_type} client",
            context={"type": client_type, "error": str(e)},
            cause=e
        )
