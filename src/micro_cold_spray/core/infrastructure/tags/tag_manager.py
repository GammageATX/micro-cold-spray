from typing import Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

from ...config.config_manager import ConfigManager
from ..messaging.message_broker import MessageBroker
from ...hardware.communication.plc_client import PLCClient
from ...hardware.communication.ssh_client import SSHClient

logger = logging.getLogger(__name__)

class TagManager:
    """Manages system tags and their values."""
    
    def __init__(self, config_manager: ConfigManager, message_broker: MessageBroker):
        self._config_manager = config_manager
        self._message_broker = message_broker
        self._plc_client = PLCClient(config_manager.get_config('plc'))
        self._ssh_client = SSHClient(config_manager.get_config('ssh'))
        
        # Subscribe to relevant topics
        self._message_broker.subscribe("tag/set", self._handle_tag_set)
        self._message_broker.subscribe("tag/get", self._handle_tag_get)
        
        logger.info("TagManager initialized")

    async def _handle_tag_set(self, data: Dict[str, Any]) -> None:
        """Handle setting a tag value."""
        tag = data.get("tag")
        value = data.get("value")
        # Logic to set the tag value
        logger.info(f"Tag set: {tag} = {value}")

    async def _handle_tag_get(self, data: Dict[str, Any]) -> None:
        """Handle getting a tag value."""
        tag = data.get("tag")
        # Logic to get the tag value
        value = ...  # Retrieve the value
        await self._message_broker.publish("tag/get/response", {"tag": tag, "value": value})
        logger.info(f"Tag get: {tag} = {value}")

    def set_tag(self, tag: str, value: Any) -> None:
        """Set a tag value."""
        # Logic to set the tag value
        logger.info(f"Tag set: {tag} = {value}")

    def get_tag(self, tag: str) -> Any:
        """Get a tag value."""
        # Logic to get the tag value
        value = ...  # Retrieve the value
        logger.info(f"Tag get: {tag} = {value}")
        return value

    async def _publish_connection_states(self) -> None:
        """Publish current connection states through MessageBroker."""
        if self._message_broker is None:
            logger.error("Cannot publish connection states - no message broker")
            return
        
        await self._message_broker.publish('hardware_status', {
            'plc_connected': self.is_plc_connected(),
            'ssh_connected': self.is_ssh_connected(),
            'timestamp': datetime.now().isoformat()
        })

    async def _poll_hardware_tags(self) -> None:
        """Poll hardware for tag updates."""
        last_plc_state = None
        last_ssh_state = None
        
        while True:
            try:
                # Check for connection state changes
                plc_state = self.is_plc_connected()
                ssh_state = self.is_ssh_connected()
                
                if plc_state != last_plc_state or ssh_state != last_ssh_state:
                    await self._publish_connection_states()
                    last_plc_state = plc_state
                    last_ssh_state = ssh_state
                
                # Only poll PLC tags - they contain all critical hardware status
                if self._plc_client and self._plc_client.is_connected:
                    for group, tags in self._tag_definitions.items():
                        for tag_name, tag_def in tags.items():
                            if tag_def.get('mapped') and tag_def.get('plc_tag'):
                                value = await self._plc_client.read_tag(tag_def['plc_tag'])
                                await self._update_tag(f"{group}.{tag_name}", value)
                
                await asyncio.sleep(0.1)  # Poll rate
                
            except Exception as e:
                logger.error(f"Error polling hardware tags: {e}")
                await asyncio.sleep(1.0)  # Error recovery delay

    async def _update_tag(self, tag_name: str, value: Any) -> None:
        """Update tag value and publish change."""
        if self._message_broker is None:
            logger.error("Cannot update tag - no message broker")
            return
        
        if self._tag_values.get(tag_name) != value:
            self._tag_values[tag_name] = value
            await self._message_broker.publish('tag_update', {tag_name: value})

    def _get_tag_definition(self, tag_name: str) -> Dict[str, Any]:
        """Get tag definition from config."""
        if '.' in tag_name:
            group, name = tag_name.split('.', 1)
            return self._tag_definitions.get(group, {}).get(name, {})
        return {}

    def _validate_tag_value(self, value: Any, tag_def: Dict[str, Any]) -> bool:
        """Validate tag value against its definition."""
        tag_type = tag_def.get('type')
        if tag_type == 'string':
            return isinstance(value, str)
        elif tag_type == 'float':
            return isinstance(value, (int, float))
        elif tag_type == 'bool':
            return isinstance(value, bool)
        return True  # Allow unknown types

    def is_plc_connected(self) -> bool:
        """Check if PLC connection is active."""
        return self._plc_client is not None and self._plc_client.is_connected

    def is_ssh_connected(self) -> bool:
        """Check if SSH connection is active."""
        return self._ssh_client is not None and self._ssh_client.is_connected

    async def attempt_reconnect(self) -> None:
        """Attempt to reconnect to hardware clients."""
        try:
            if self._plc_client:
                await self._plc_client.connect()
            if self._ssh_client:
                await self._ssh_client.connect()
            
            # Publish updated connection states after reconnection attempt
            await self._publish_connection_states()
            
        except Exception as e:
            logger.error(f"Error during reconnection attempt: {e}")
            raise