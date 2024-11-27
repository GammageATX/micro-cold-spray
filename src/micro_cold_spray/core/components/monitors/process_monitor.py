"""Process monitoring component."""
import logging
from typing import Dict, Any

from ...infrastructure.messaging.message_broker import MessageBroker
from ...infrastructure.tags.tag_manager import TagManager
from ...config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class ProcessMonitor:
    """Monitors process status and publishes updates."""

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
        
        # Subscribe to process-related messages
        self._message_broker.subscribe(
            "process/status",
            self._handle_process_status
        )
        
        logger.info("Process monitor initialized")

    async def _handle_process_status(self, data: Dict[str, Any]) -> None:
        """Handle process status updates."""
        try:
            # Update process status tags
            for parameter, value in data.items():
                self._tag_manager.set_tag(f"process.status.{parameter}", value)
                
            # Publish consolidated status
            await self._message_broker.publish(
                "process/status/updated",
                {
                    "status": data,
                    "timestamp": self._tag_manager.get_tag("system.timestamp")
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling process status: {e}")

    async def start(self) -> None:
        """Start monitoring."""
        logger.info("Process monitoring started")

    async def stop(self) -> None:
        """Stop monitoring."""
        logger.info("Process monitoring stopped")