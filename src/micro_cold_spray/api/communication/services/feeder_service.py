"""Feeder controller service implementation."""

from typing import Any
from loguru import logger

from .. import HardwareError
from .tag_mapping import TagMappingService
from .tag_cache import TagCacheService
from ..clients import SSHClient, create_ssh_client


class FeederTagService:
    """Service for managing feeder controller via SSH."""

    def __init__(self, config_service):
        """Initialize feeder service."""
        self._config_service = config_service
        self._ssh_client: SSHClient = None
        self._tag_mapping: TagMappingService = None
        self._tag_cache: TagCacheService = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def start(self) -> None:
        """Initialize service."""
        # Load hardware config
        hw_config = await self._config_service.get_config("hardware")
        
        # Create SSH client
        self._ssh_client = create_ssh_client(hw_config)
        await self._ssh_client.connect()
        
        # Initialize tag services
        self._tag_mapping = TagMappingService(self._config_service)
        await self._tag_mapping.start()
        
        self._tag_cache = TagCacheService(self._config_service)
        await self._tag_cache.start()
        
        self._is_running = True
        logger.info("Feeder service initialized")

    async def stop(self) -> None:
        """Cleanup service."""
        self._is_running = False
        
        if self._ssh_client:
            await self._ssh_client.disconnect()
            
        if self._tag_mapping:
            await self._tag_mapping.stop()
            
        if self._tag_cache:
            await self._tag_cache.stop()
            
        logger.info("Feeder service stopped")

    def _build_command(self, mapped_name: str, value: Any) -> str:
        """Build P variable command string."""
        hw_tag = self._tag_mapping.to_hardware_tag(mapped_name)
        return f"{hw_tag}={value}"

    async def write_tag(self, mapped_name: str, value: Any) -> None:
        """Write P variable via SSH."""
        if not self.is_running:
            raise HardwareError(
                "Feeder service not running",
                "feeder",
                {"mapped_name": mapped_name}
            )
            
        if not self._tag_mapping.is_feeder_tag(mapped_name):
            raise HardwareError(
                f"Not a feeder tag: {mapped_name}",
                "feeder",
                {"mapped_name": mapped_name}
            )
            
        try:
            command = self._build_command(mapped_name, value)
            await self._ssh_client.write_command(command)
            self._tag_cache.update_tag(mapped_name, value)
            logger.debug(f"Set feeder tag {mapped_name} = {value}")
        except Exception as e:
            raise HardwareError(
                f"Failed to write feeder tag: {str(e)}",
                "feeder",
                {
                    "mapped_name": mapped_name,
                    "value": value,
                    "error": str(e)
                }
            )

    async def read_tag(self, mapped_name: str) -> Any:
        """Get last known value from cache."""
        if not self.is_running:
            raise HardwareError(
                "Feeder service not running",
                "feeder",
                {"mapped_name": mapped_name}
            )
            
        if not self._tag_mapping.is_feeder_tag(mapped_name):
            raise HardwareError(
                f"Not a feeder tag: {mapped_name}",
                "feeder",
                {"mapped_name": mapped_name}
            )
            
        return self._tag_cache.get_tag(mapped_name)

    async def check_connection(self) -> bool:
        """Check if feeder controller is accessible."""
        try:
            if not self.is_running:
                return False
                
            return await self._ssh_client.test_connection()
        except Exception as e:
            logger.error(f"Feeder connection check failed: {str(e)}")
            return False
