"""Communication service for hardware control."""

from typing import Dict, Any, Optional
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_errors import create_error
from .clients import create_client, CommunicationClient


class CommunicationService(ConfigurableService):
    """Service for managing hardware communication."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize communication service.
        
        Args:
            config: Service configuration
        """
        super().__init__(service_name="communication")
        self._config = config or {}
        self._client: Optional[CommunicationClient] = None
        logger.info("CommunicationService initialized")

    @property
    def client(self) -> CommunicationClient:
        """Get the active client instance.
        
        Returns:
            Active client instance
            
        Raises:
            HTTPException: If no client is initialized
        """
        if not self._client:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="No communication client initialized",
                context={"service": self._service_name}
            )
        return self._client

    async def _start(self) -> None:
        """Start communication service.
        
        Raises:
            HTTPException: If service fails to start
        """
        try:
            # Extract client config
            client_type = self._config.get("client_type", "mock")
            client_config = self._config.get("client_config", {})
            
            # Create and start client
            self._client = create_client(client_type, client_config)
            await self._client.start()
            
            logger.info(f"Started {client_type} client")
            
        except Exception as e:
            error_msg = f"Failed to start communication service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"service": self._service_name},
                cause=e
            )

    async def _stop(self) -> None:
        """Stop communication service.
        
        Raises:
            HTTPException: If service fails to stop
        """
        try:
            if self._client:
                await self._client.stop()
                self._client = None
            logger.info("Stopped communication service")
        except Exception as e:
            error_msg = f"Failed to stop communication service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"service": self._service_name},
                cause=e
            )

    async def read_tag(self, tag: str) -> Any:
        """Read tag value from hardware.
        
        Args:
            tag: Tag to read
            
        Returns:
            Tag value
            
        Raises:
            HTTPException: If read fails
        """
        try:
            return await self.client.read_tag(tag)
        except Exception as e:
            error_msg = f"Failed to read tag {tag}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"tag": tag},
                cause=e
            )

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write tag value to hardware.
        
        Args:
            tag: Tag to write
            value: Value to write
            
        Raises:
            HTTPException: If write fails
        """
        try:
            await self.client.write_tag(tag, value)
        except Exception as e:
            error_msg = f"Failed to write tag {tag}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"tag": tag, "value": value},
                cause=e
            )

    async def check_connection(self) -> bool:
        """Check if hardware connection is healthy.
        
        Returns:
            True if connection is healthy
        """
        try:
            if not self._client:
                return False
            return await self._client.check_connection()
        except Exception as e:
            logger.warning(f"Connection check failed: {e}")
            return False
