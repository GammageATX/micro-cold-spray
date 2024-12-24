"""Base class for communication clients."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from loguru import logger

from micro_cold_spray.utils.errors import create_error


class CommunicationClient(ABC):
    """Abstract base class for communication clients."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize communication client.
        
        Args:
            config: Client configuration from communication.yaml
        """
        self._config = config
        self._connected = False
        logger.info(f"Initialized {self.__class__.__name__}")

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to device.
        
        Raises:
            HTTPException: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to device.
        
        Raises:
            HTTPException: If disconnect fails
        """
        pass

    @abstractmethod
    async def read_tag(self, tag: str) -> Any:
        """Read single tag value.
        
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
        """Write tag value.
        
        Args:
            tag: Tag to write
            value: Value to write
            
        Raises:
            HTTPException: If write fails
        """
        pass
