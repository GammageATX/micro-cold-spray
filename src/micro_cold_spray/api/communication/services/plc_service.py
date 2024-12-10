from typing import Any
import asyncio
from loguru import logger

from .base import BaseService
from .tag_mapping import TagMappingService
from .tag_cache import TagCacheService
from ..clients import PLCClient, create_plc_client
from ....core.exceptions import HardwareError
from ....core.infrastructure.config.config_manager import ConfigManager


class PLCTagService(BaseService):
    """Handles PLC tag operations and caching."""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self._plc_client: PLCClient = None
        self._tag_mapping: TagMappingService = None
        self._tag_cache: TagCacheService = None
        self._polling_task = None

    async def initialize(self):
        """Initialize service with config and start polling."""
        await super().initialize()
        
        # Initialize services
        self._tag_mapping = TagMappingService(self._config_manager)
        await self._tag_mapping.initialize()
        
        self._tag_cache = TagCacheService(self._config_manager)
        await self._tag_cache.initialize()
        
        # Create PLC client from config
        self._plc_client = create_plc_client(self._hw_config)
        await self._plc_client.connect()

        # Get polling interval from config
        self._poll_interval = self._hw_config.get('network', {}).get(
            'plc', {}).get('polling_interval', 1.0)

        # Start polling
        self._polling_task = asyncio.create_task(self._poll_tags())
        logger.info("PLC tag polling started")

    async def _poll_tags(self):
        """Poll PLC for mapped tag updates."""
        while True:
            try:
                # Get all hardware tag values
                hw_values = await self._plc_client.get_all_tags()
                
                # Convert hardware tags to mapped names and update cache
                for hw_tag, value in hw_values.items():
                    try:
                        mapped_name = self._tag_mapping.to_mapped_name(hw_tag)
                        self._tag_cache.update_tag(mapped_name, value)
                    except HardwareError:
                        # Skip unmapped tags
                        continue
                        
                logger.debug(f"Updated {len(hw_values)} PLC tags")
            except Exception as e:
                logger.error(f"Error polling PLC tags: {e}")
            await asyncio.sleep(self._poll_interval)

    async def read_tag(self, mapped_name: str) -> Any:
        """Get cached tag value."""
        if not self._tag_mapping.is_plc_tag(mapped_name):
            raise HardwareError(f"Not a PLC tag: {mapped_name}", "plc")
        return self._tag_cache.get_tag(mapped_name)

    async def write_tag(self, mapped_name: str, value: Any):
        """Write tag value to PLC."""
        try:
            if not self._tag_mapping.is_plc_tag(mapped_name):
                raise HardwareError(f"Not a PLC tag: {mapped_name}", "plc")
                
            # Convert to hardware tag
            hw_tag = self._tag_mapping.to_hardware_tag(mapped_name)
            
            # Write and update cache
            await self._plc_client.write_tag(hw_tag, value)
            self._tag_cache.update_tag(mapped_name, value)
        except Exception as e:
            raise HardwareError(f"Failed to write tag {mapped_name}: {e}", "plc")

    async def _on_hardware_config_update(self):
        """Handle hardware config updates."""
        # Update polling interval
        self._poll_interval = self._hw_config.get('network', {}).get(
            'plc', {}).get('polling_interval', 1.0)
        
        # Reconnect PLC client if connection settings changed
        await self._plc_client.disconnect()
        self._plc_client = create_plc_client(self._hw_config)
        await self._plc_client.connect()

    async def shutdown(self):
        """Cleanup PLC connections."""
        await super().shutdown()
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        if self._plc_client:
            await self._plc_client.disconnect()
        logger.info("PLC service shutdown complete")
