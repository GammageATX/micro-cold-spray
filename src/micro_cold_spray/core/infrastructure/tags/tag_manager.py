from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from datetime import datetime

from ..messaging.message_broker import MessageBroker
from ...config.config_manager import ConfigManager
from ...hardware.communication.plc_client import PLCClient
from ...hardware.communication.ssh_client import SSHClient
from ...exceptions import TagOperationError

class TagManager:
    """
    Manages system tags and hardware communication.
    Single Source of Truth for all hardware interactions.
    """
    
    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager
    ):
        """Initialize with required dependencies."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        
        # Hardware clients
        self._plc_client: Optional[PLCClient] = None
        self._ssh_client: Optional[SSHClient] = None
        
        # Tag management
        self._tag_config = {}  # Full tag configuration from tags.yaml
        self._tag_values: Dict[str, Any] = {}  # Current tag values
        self._plc_tag_map: Dict[str, str] = {}  # Maps system tags to PLC tags
        self._polling_task: Optional[asyncio.Task] = None
        self._is_initialized = False
        
        logger.info("TagManager initialized")

    async def initialize(self) -> None:
        """Initialize tag manager and hardware connections."""
        try:
            if self._is_initialized:
                return

            # Load tag configuration
            self._tag_config = self._config_manager.get_config('tags')
            self._build_tag_maps()

            # Create hardware clients
            hw_config = self._config_manager.get_config('hardware')
            self._plc_client = PLCClient(hw_config)
            self._ssh_client = SSHClient(hw_config)

            # Connect SSH client (PLC doesn't need explicit connection)
            await self._ssh_client.connect()

            # Subscribe to tag operations
            await self._message_broker.subscribe("tag/set", self._handle_tag_set)
            await self._message_broker.subscribe("tag/get", self._handle_tag_get)

            # Start polling
            self._polling_task = asyncio.create_task(self._poll_tags())
            
            self._is_initialized = True
            logger.info("TagManager initialization complete")

        except Exception as e:
            logger.exception("Failed to initialize TagManager")
            raise TagOperationError(f"TagManager initialization failed: {str(e)}") from e

    def _build_tag_maps(self) -> None:
        """Build mappings from tag configuration."""
        def process_group(group: Dict[str, Any], prefix: str = ""):
            for name, config in group.items():
                full_name = f"{prefix}.{name}" if prefix else name
                
                if isinstance(config, dict):
                    if config.get('mapped') and config.get('plc_tag'):
                        self._plc_tag_map[full_name] = config['plc_tag']
                    elif 'ssh' in config:
                        # SSH tags are handled directly
                        pass
                    elif not config.get('internal', False):
                        process_group(config, full_name)

        process_group(self._tag_config.get('tag_groups', {}))

    async def _poll_tags(self) -> None:
        """Poll PLC tags and publish updates."""
        while True:
            try:
                # Get all PLC tags
                plc_tags = await self._plc_client.get_all_tags()
                
                # Update mapped tag values
                for sys_tag, plc_tag in self._plc_tag_map.items():
                    if plc_tag in plc_tags:
                        value = plc_tags[plc_tag]
                        if self._tag_values.get(sys_tag) != value:
                            self._tag_values[sys_tag] = value
                            await self._message_broker.publish(
                                "tag/update",
                                {sys_tag: value}
                            )
                
                await asyncio.sleep(0.1)  # Poll rate

            except Exception as e:
                logger.error(f"Error polling tags: {e}")
                await self._message_broker.publish(
                    "hardware/connection",
                    {"connected": False}
                )
                await asyncio.sleep(1.0)  # Error recovery delay

    async def _handle_tag_set(self, data: Dict[str, Any]) -> None:
        """Handle tag set requests."""
        try:
            tag_name = data.get('tag')
            value = data.get('value')
            
            if not tag_name:
                raise ValueError("Missing tag name")

            # Get tag configuration
            tag_path = tag_name.split('.')
            current = self._tag_config.get('tag_groups', {})
            for part in tag_path:
                current = current.get(part, {})

            # Handle PLC tags
            if current.get('mapped') and current.get('plc_tag'):
                plc_tag = current['plc_tag']
                await self._plc_client.write_tag(plc_tag, value)
                self._tag_values[tag_name] = value
                
            # Handle SSH feeder commands
            elif 'ssh' in current:
                ssh_config = current['ssh']
                freq_var = ssh_config['freq_var']
                time_var = ssh_config['time_var']
                start_var = ssh_config['start_var']
                
                # Set frequency
                await self._ssh_client.write_command(f"set {freq_var}={value}")
                # Set time
                await self._ssh_client.write_command(f"set {time_var}={ssh_config['default_time']}")
                # Start feeder
                await self._ssh_client.write_command(f"set {start_var}={ssh_config['start_val']}")
                
            # Handle internal tags
            elif current.get('internal', False):
                self._tag_values[tag_name] = value
                await self._message_broker.publish(
                    "tag/update",
                    {tag_name: value}
                )
                
            else:
                raise ValueError(f"Unknown tag: {tag_name}")

        except Exception as e:
            logger.error(f"Error setting tag {tag_name}: {e}")
            raise TagOperationError(f"Failed to set tag: {str(e)}") from e

    async def _handle_tag_get(self, data: Dict[str, Any]) -> None:
        """Handle tag get requests."""
        try:
            tag_name = data.get('tag')
            if not tag_name:
                raise ValueError("Missing tag name")

            if tag_name not in self._tag_values:
                raise ValueError(f"Unknown tag: {tag_name}")

            await self._message_broker.publish(
                "tag/get/response",
                {
                    "tag": tag_name,
                    "value": self._tag_values[tag_name]
                }
            )

        except Exception as e:
            logger.error(f"Error getting tag {tag_name}: {e}")
            raise TagOperationError(f"Failed to get tag: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown tag manager."""
        try:
            if self._polling_task:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass

            if self._ssh_client:
                await self._ssh_client.disconnect()

            self._is_initialized = False
            logger.info("TagManager shutdown complete")

        except Exception as e:
            logger.exception("Error during TagManager shutdown")
            raise TagOperationError(f"TagManager shutdown failed: {str(e)}") from e