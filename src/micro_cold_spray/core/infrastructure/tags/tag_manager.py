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
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TagManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._tag_values: Dict[str, Any] = {}
        self._tag_definitions: Dict[str, Any] = {}
        self._motion_limits: Dict[str, Any] = {}
        self._message_broker = None
        self._config = None
        self._tags = {}
        self._connected = False
        self._initialized = True
        
        # Hardware clients
        self._plc_client: Optional[PLCClient] = None
        self._ssh_client: Optional[SSHClient] = None
        
        logger.info("Tag manager initialized")

    def set_message_broker(self, message_broker: MessageBroker) -> None:
        """Set message broker instance."""
        self._message_broker = message_broker
        
        # Subscribe to tag commands
        self._message_broker.subscribe("tag/set", self._handle_tag_set)
        self._message_broker.subscribe("tag/get", self._handle_tag_get)
        
        logger.info("Tag manager subscribed to message broker")

    def load_config(self, config_manager: ConfigManager) -> None:
        """Load configuration from config manager."""
        try:
            self._config = config_manager.get_config("tags")
            # Load tag definitions from config
            self._tag_definitions = self._config.get('tag_groups', {})
            
            # Load hardware config
            hw_config = config_manager.get_config('hardware')['hardware']
            
            # Initialize hardware clients
            self._plc_client = PLCClient(hw_config)
            self._ssh_client = SSHClient(config_manager, self._message_broker)
            
            # Start tag polling
            self._polling_task = asyncio.create_task(self._poll_hardware_tags())
            
            # Publish initial connection states
            asyncio.create_task(self._publish_connection_states())
            
            logger.info("Tag manager initialized with hardware clients")
            
        except Exception as e:
            logger.error(f"Error loading tag manager config: {e}")
            raise

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

    async def _handle_tag_set(self, data: Dict[str, Any]) -> None:
        """Handle tag set requests."""
        try:
            tag = data.get("tag")
            value = data.get("value")
            source = data.get("source", "unknown")
            
            if tag and value is not None:
                logger.debug(f"Setting tag {tag} to {value} from {source}")
                await self._update_tag(tag, value)
            
        except Exception as e:
            logger.error(f"Error handling tag set: {e}")
            raise

    async def _handle_tag_get(self, data: Dict[str, Any]) -> None:
        """Handle tag get requests."""
        if self._message_broker is None:
            logger.error("Cannot handle tag get - no message broker")
            return
        
        tag_name = data.get('tag')
        if tag_name:
            value = self._tag_values.get(tag_name)
            await self._message_broker.publish('tag_get_response', {
                'tag': tag_name,
                'value': value
            })

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

    def get_tag(self, tag_name: str) -> Any:
        """Get tag value from local cache."""
        return self._tag_values.get(tag_name)

    async def set_tag(self, tag_name: str, value: Any) -> None:
        """Set tag value and update hardware if needed."""
        await self._handle_tag_set({
            'tag': tag_name,
            'value': value
        })