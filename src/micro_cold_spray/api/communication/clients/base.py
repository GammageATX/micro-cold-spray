"""Base client for hardware communication."""

from abc import ABC, abstractmethod
from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_errors import create_error


class CommunicationClient(ABC, ConfigurableService):
    """Base class for hardware communication clients."""

    def __init__(self, client_name: str, config: Dict[str, Any]):
        """Initialize client.
        
        Args:
            client_name: Name of client for logging
            config: Client configuration
        """
        super().__init__(service_name=f"{client_name}_client")
        self._config = config or {}  # Ensure config is never None
        self._connection = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to hardware.
        
        Raises:
            HTTPException: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to hardware.
        
        Raises:
            HTTPException: If disconnect fails
        """
        pass

    @abstractmethod
    async def read_tag(self, tag: str) -> Any:
        """Read tag value from hardware.
        
        Args:
            tag: Tag to read
            
        Returns:
            Tag value
            
        Raises:
            HTTPException: If read fails
        """
        pass

    @abstractmethod
    async def write_tag(self, tag: str, value: Any) -> None:
        """Write tag value to hardware.
        
        Args:
            tag: Tag to write
            value: Value to write
            
        Raises:
            HTTPException: If write fails
        """
        pass

    async def _start(self) -> None:
        """Start client service."""
        try:
            await self.connect()
            logger.info(f"{self._service_name} started")
        except Exception as e:
            error_msg = f"Failed to start {self._service_name}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"device": self._service_name},
                cause=e
            )

    async def _stop(self) -> None:
        """Stop client service."""
        try:
            if self.is_connected:
                await self.disconnect()
            logger.info(f"{self._service_name} stopped")
        except Exception as e:
            error_msg = f"Failed to stop {self._service_name}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"device": self._service_name},
                cause=e
            )

    async def check_connection(self) -> bool:
        """Check if connection is healthy.
        
        Returns:
            True if connection is healthy
        """
        try:
            if not self.is_connected:
                return False
                
            # Try to read a test tag
            test_tag = self._config.get("test_tag")
            if test_tag:
                await self.read_tag(test_tag)
                
            return True
            
        except Exception as e:
            logger.warning(f"Connection check failed for {self._service_name}: {e}")
            return False
