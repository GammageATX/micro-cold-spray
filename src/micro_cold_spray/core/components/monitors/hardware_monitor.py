"""Hardware monitoring component."""
import logging
from typing import Dict, Any

from ...infrastructure.messaging.message_broker import MessageBroker
from ...infrastructure.tags.tag_manager import TagManager
from ...config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class HardwareMonitor:
    """Monitors hardware status and publishes updates."""

    def __init__(self, tag_manager: TagManager, message_broker: MessageBroker):
        """Initialize monitor.
        
        Args:
            tag_manager: Tag manager instance
            message_broker: Message broker instance
        """
        self._tag_manager = tag_manager
        self._message_broker = message_broker
        self._config_manager = ConfigManager()
        
        # Load message types from config
        self._message_types = self._config_manager.get_config('messaging').get('message_types', {})
        
        # Subscribe to hardware-related messages
        self._message_broker.subscribe(
            "hardware/status",
            self._handle_hardware_status
        )
        
        logger.info("Hardware monitor initialized")

    def _handle_hardware_status(self, data: Dict[str, Any]) -> None:
        """Handle hardware status updates."""
        try:
            # Update hardware status tags
            for component, status in data.items():
                self._tag_manager.set_tag(f"hardware.status.{component}", status)
                
            # Publish consolidated status
            self._message_broker.publish(
                "hardware/status/updated",
                {
                    "status": data,
                    "timestamp": self._tag_manager.get_tag("system.timestamp")
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling hardware status: {e}")

    async def start(self) -> None:
        """Start monitoring."""
        logger.info("Hardware monitoring started")

    async def stop(self) -> None:
        """Stop monitoring."""
        logger.info("Hardware monitoring stopped")