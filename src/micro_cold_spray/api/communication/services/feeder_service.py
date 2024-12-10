from typing import Any
from loguru import logger

from .base import BaseService
from .tag_mapping import TagMappingService
from .tag_cache import TagCacheService
from ..clients import SSHClient, create_ssh_client
from ....core.exceptions import HardwareError
from ....core.infrastructure.config.config_manager import ConfigManager


class FeederTagService(BaseService):
    """Handles feeder control via SSH."""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self._ssh_client: SSHClient = None
        self._tag_mapping: TagMappingService = None
        self._tag_cache: TagCacheService = None

    async def initialize(self):
        """Initialize service with config."""
        await super().initialize()
        
        # Initialize services
        self._tag_mapping = TagMappingService(self._config_manager)
        await self._tag_mapping.initialize()
        
        self._tag_cache = TagCacheService(self._config_manager)
        await self._tag_cache.initialize()
        
        # Create SSH client from config
        self._ssh_client = create_ssh_client(self._hw_config)
        await self._ssh_client.connect()

        logger.info("Feeder service initialized")

    def _build_p_var_command(self, mapped_name: str, value: Any) -> str:
        """Build P variable command string."""
        hw_tag = self._tag_mapping.to_hardware_tag(mapped_name)
        return f"{hw_tag}={value}"

    async def write_tag(self, mapped_name: str, value: Any):
        """Write P variable via SSH."""
        try:
            if not self._tag_mapping.is_feeder_tag(mapped_name):
                raise HardwareError(f"Not a feeder tag: {mapped_name}", "feeder")
                
            command = self._build_p_var_command(mapped_name, value)
            await self._ssh_client.write_command(command)
            self._tag_cache.update_tag(mapped_name, value)
            logger.debug(f"Set feeder tag {mapped_name} = {value}")
        except Exception as e:
            raise HardwareError(f"Failed to write feeder tag {mapped_name}: {e}", "feeder")

    async def read_tag(self, mapped_name: str) -> Any:
        """Get last known value from cache."""
        if not self._tag_mapping.is_feeder_tag(mapped_name):
            raise HardwareError(f"Not a feeder tag: {mapped_name}", "feeder")
        return self._tag_cache.get_tag(mapped_name)

    async def _on_hardware_config_update(self):
        """Handle hardware config updates."""
        # Reconnect SSH client if connection settings changed
        await self._ssh_client.disconnect()
        self._ssh_client = create_ssh_client(self._hw_config)
        await self._ssh_client.connect()

    async def shutdown(self):
        """Cleanup SSH connections."""
        await super().shutdown()
        if self._ssh_client:
            await self._ssh_client.disconnect()
        logger.info("Feeder service shutdown complete")
