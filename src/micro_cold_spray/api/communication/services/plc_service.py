"""PLC communication service implementation."""

from typing import Any
from loguru import logger

from .. import HardwareError
from .tag_mapping import TagMappingService
from .tag_cache import TagCacheService
from ..clients import PLCClient, create_plc_client


class PLCTagService:
    """Service for managing PLC communication."""

    def __init__(self, config_service):
        """Initialize PLC service."""
        self._config_service = config_service
        self._plc_client: PLCClient = None
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
        
        # Create PLC client
        self._plc_client = create_plc_client(hw_config)
        await self._plc_client.connect()
        
        # Initialize tag services
        self._tag_mapping = TagMappingService(self._config_service)
        await self._tag_mapping.start()
        
        self._tag_cache = TagCacheService(self._config_service)
        await self._tag_cache.start()
        
        # Initial tag read
        await self._read_all_tags()
        
        self._is_running = True
        logger.info("PLC service initialized")

    async def stop(self) -> None:
        """Cleanup service."""
        self._is_running = False
        
        if self._plc_client:
            await self._plc_client.disconnect()
            
        if self._tag_mapping:
            await self._tag_mapping.stop()
            
        if self._tag_cache:
            await self._tag_cache.stop()
            
        logger.info("PLC service stopped")

    async def _read_all_tags(self) -> None:
        """Read all tags from PLC and update cache."""
        try:
            tag_values = await self._plc_client.get_all_tags()
            for hw_tag, value in tag_values.items():
                try:
                    mapped_name = self._tag_mapping.to_mapped_name(hw_tag)
                    self._tag_cache.update_tag(mapped_name, value)
                except HardwareError:
                    # Skip unmapped tags
                    continue
                    
            logger.debug("Updated all PLC tags")
        except Exception as e:
            logger.error(f"Failed to read all tags: {str(e)}")
            raise HardwareError(
                "Failed to read all tags",
                "plc",
                {"error": str(e)}
            )

    async def read_tag(self, mapped_name: str) -> Any:
        """Read tag value from PLC."""
        if not self.is_running:
            raise HardwareError(
                "PLC service not running",
                "plc",
                {"mapped_name": mapped_name}
            )
            
        if not self._tag_mapping.is_plc_tag(mapped_name):
            raise HardwareError(
                f"Not a PLC tag: {mapped_name}",
                "plc",
                {"mapped_name": mapped_name}
            )
            
        try:
            hw_tag = self._tag_mapping.to_hardware_tag(mapped_name)
            value = await self._plc_client.read_tag(hw_tag)
            self._tag_cache.update_tag(mapped_name, value)
            return value
        except Exception as e:
            raise HardwareError(
                f"Failed to read tag: {str(e)}",
                "plc",
                {
                    "mapped_name": mapped_name,
                    "error": str(e)
                }
            )

    async def write_tag(self, mapped_name: str, value: Any) -> None:
        """Write tag value to PLC."""
        if not self.is_running:
            raise HardwareError(
                "PLC service not running",
                "plc",
                {"mapped_name": mapped_name}
            )
            
        if not self._tag_mapping.is_plc_tag(mapped_name):
            raise HardwareError(
                f"Not a PLC tag: {mapped_name}",
                "plc",
                {"mapped_name": mapped_name}
            )
            
        try:
            hw_tag = self._tag_mapping.to_hardware_tag(mapped_name)
            await self._plc_client.write_tag(hw_tag, value)
            self._tag_cache.update_tag(mapped_name, value)
            logger.debug(f"Wrote {value} to {mapped_name}")
        except Exception as e:
            raise HardwareError(
                f"Failed to write tag: {str(e)}",
                "plc",
                {
                    "mapped_name": mapped_name,
                    "value": value,
                    "error": str(e)
                }
            )

    async def check_connection(self) -> bool:
        """Check if PLC is accessible."""
        try:
            if not self.is_running:
                return False
                
            # Try reading a test tag
            await self._plc_client.read_tag("System.Heartbeat")
            return True
        except Exception as e:
            logger.error(f"PLC connection check failed: {str(e)}")
            return False
