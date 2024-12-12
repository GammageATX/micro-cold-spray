"""Feeder tag service for communication with feeder devices."""

from typing import Dict, Any
from loguru import logger

from ...base import ConfigurableService
from ...config import ConfigService
from ...messaging import MessagingService
from ..exceptions import HardwareError
from .tag_cache import TagCacheService


class FeederTagService(ConfigurableService):
    """Service for feeder tag communication."""

    def __init__(
        self,
        config_manager: ConfigService,
        message_broker: MessagingService,
        tag_cache: TagCacheService
    ):
        """Initialize feeder tag service.
        
        Args:
            config_manager: Configuration service instance
            message_broker: Messaging service instance
            tag_cache: Tag cache service instance
        """
        super().__init__(service_name="feeder_tag")
        self._config_manager = config_manager
        self._message_broker = message_broker
        self._tag_cache = tag_cache
        self._connected = False

    async def _start(self) -> None:
        """Start feeder tag service."""
        try:
            # Load config
            config = await self._config_manager.get_config("communication")
            await self.configure(config)

            # Initialize feeder connection
            await self._connect()
            
            # Subscribe to tag updates
            await self._subscribe_to_updates()
            
            logger.info("Feeder tag service started")
            
        except Exception as e:
            logger.error(f"Failed to start feeder tag service: {e}")
            await self._cleanup()
            raise

    async def _stop(self) -> None:
        """Stop feeder tag service."""
        await self._cleanup()
        logger.info("Feeder tag service stopped")

    async def _cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self._connected:
                await self._disconnect()
        except Exception as e:
            logger.error(f"Error during feeder tag service cleanup: {e}")

    async def _connect(self) -> None:
        """Establish connection to feeder."""
        try:
            # Connection logic here
            self._connected = True
            logger.info("Connected to feeder")
        except Exception as e:
            raise HardwareError(
                "Failed to connect to feeder",
                "feeder_connection",
                {"error": str(e)}
            )

    async def _disconnect(self) -> None:
        """Disconnect from feeder."""
        try:
            # Disconnection logic here
            self._connected = False
            logger.info("Disconnected from feeder")
        except Exception as e:
            logger.error(f"Error disconnecting from feeder: {e}")

    async def _subscribe_to_updates(self) -> None:
        """Subscribe to feeder tag updates."""
        try:
            # Subscribe to relevant topics
            await self._message_broker.subscribe(
                "feeder.tags.update",
                self._handle_tag_update
            )
        except Exception as e:
            raise HardwareError(
                "Failed to subscribe to feeder updates",
                "feeder_subscription",
                {"error": str(e)}
            )

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle incoming tag updates.
        
        Args:
            data: Tag update data
        """
        try:
            # Process tag update
            tag = data.get("tag")
            value = data.get("value")
            if tag and value is not None:
                await self._tag_cache.update_value(tag, value)
        except Exception as e:
            logger.error(f"Error handling tag update: {e}")

    async def read_tag(self, tag: str) -> Any:
        """Read a feeder tag value.
        
        Args:
            tag: Tag to read
            
        Returns:
            Tag value
            
        Raises:
            HardwareError: If tag read fails
        """
        try:
            # Read tag value
            value = await self._tag_cache.get_value(tag)
            return value
        except Exception as e:
            raise HardwareError(
                f"Failed to read tag {tag}",
                "feeder_read",
                {"error": str(e)}
            )

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write a feeder tag value.
        
        Args:
            tag: Tag to write
            value: Value to write
            
        Raises:
            HardwareError: If tag write fails
        """
        try:
            # Write tag value
            await self._tag_cache.write_value(tag, value)
        except Exception as e:
            raise HardwareError(
                f"Failed to write tag {tag}",
                "feeder_write",
                {"error": str(e)}
            )

    async def set_speed(self, speed: float) -> None:
        """Set feeder speed.
        
        Args:
            speed: Speed value in RPM
            
        Raises:
            HardwareError: If speed setting fails
        """
        try:
            await self.write_tag("feeder.speed.setpoint", speed)
        except Exception as e:
            raise HardwareError(
                "Failed to set feeder speed",
                "feeder_speed",
                {"error": str(e), "speed": speed}
            )

    async def start_feeder(self) -> None:
        """Start the feeder.
        
        Raises:
            HardwareError: If start operation fails
        """
        try:
            await self.write_tag("feeder.control.start", True)
        except Exception as e:
            raise HardwareError(
                "Failed to start feeder",
                "feeder_start",
                {"error": str(e)}
            )

    async def stop_feeder(self) -> None:
        """Stop the feeder.
        
        Raises:
            HardwareError: If stop operation fails
        """
        try:
            await self.write_tag("feeder.control.start", False)
        except Exception as e:
            raise HardwareError(
                "Failed to stop feeder",
                "feeder_stop",
                {"error": str(e)}
            )

    @property
    def is_connected(self) -> bool:
        """Check if connected to feeder."""
        return self._connected
