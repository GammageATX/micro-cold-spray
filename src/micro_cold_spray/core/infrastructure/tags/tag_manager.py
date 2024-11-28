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

    async def test_connections(self) -> Dict[str, bool]:
        """Test connections to all hardware clients.
        
        Returns:
            Dict with connection status for each client
            Example: {"plc": True, "motion_controller": False}
        """
        results = {
            "plc": False,
            "motion_controller": False
        }
        
        # Test PLC connection
        if self._plc_client:
            try:
                await self._plc_client.get_all_tags()  # Simple read test
                results["plc"] = True
            except Exception as e:
                logger.debug(f"PLC connection test failed: {e}")
        
        # Test SSH connection
        if self._ssh_client:
            try:
                await self._ssh_client.write_command("echo test")
                response = await self._ssh_client.read_response()
                results["motion_controller"] = response is not None
            except Exception as e:
                logger.debug(f"Motion controller connection test failed: {e}")
        
        return results

    async def initialize(self) -> None:
        """Initialize tag manager and hardware connections."""
        try:
            if self._is_initialized:
                return

            # Load tag configuration
            self._tag_config = self._config_manager.get_config('tags')
            self._build_tag_maps()

            # Create hardware clients if not already set (allows for mocking)
            hw_config = self._config_manager.get_config('hardware')
            if self._plc_client is None:
                self._plc_client = PLCClient(hw_config.get('plc', {}))
            if self._ssh_client is None:
                self._ssh_client = SSHClient(hw_config.get('motion_controller', {}))

            # Test connections and publish status
            connection_status = await self.test_connections()
            for device, connected in connection_status.items():
                await self._message_broker.publish(
                    "hardware/connection",
                    {
                        "device": device,
                        "connected": connected,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            # Subscribe to tag operations
            await self._message_broker.subscribe("tag/set", self._handle_tag_set)
            await self._message_broker.subscribe("tag/get", self._handle_tag_get)

            # Start polling only if PLC client is available
            try:
                await self._plc_client.get_all_tags()  # Test connection
                self._polling_task = asyncio.create_task(self._poll_tags())
                await self._message_broker.publish(
                    "hardware/connection",
                    {"device": "plc", "connected": True}
                )
            except Exception as e:
                logger.warning(f"Failed to connect to PLC: {e}")
                await self._message_broker.publish(
                    "hardware/connection",
                    {"device": "plc", "connected": False}
                )
            
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
        try:
            # Get all PLC tags
            plc_tags = await self._plc_client.get_all_tags()
            
            # Update tag values and publish changes
            for system_tag, plc_tag in self._plc_tag_map.items():
                if plc_tag in plc_tags:
                    new_value = plc_tags[plc_tag]
                    if system_tag not in self._tag_values or self._tag_values[system_tag] != new_value:
                        self._tag_values[system_tag] = new_value
                        await self._message_broker.publish("tag/update", {
                            system_tag: new_value,
                            "timestamp": datetime.now().isoformat()
                        })
                    
            # Update connection status
            await self._message_broker.publish(
                "hardware/connection",
                {
                    "device": "plc",
                    "connected": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error polling tags: {e}")
            # Report disconnected status
            await self._message_broker.publish(
                "hardware/connection",
                {
                    "device": "plc",
                    "connected": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

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
            
            # Get current value from PLC if it's a mapped tag
            if tag_name in self._plc_tag_map:
                try:
                    plc_tag = self._plc_tag_map[tag_name]
                    plc_tags = await self._plc_client.get_all_tags()
                    value = plc_tags[plc_tag]
                    
                    await self._message_broker.publish(
                        "tag/get/response",
                        {
                            "tag": tag_name,
                            "value": value,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                except Exception as e:
                    # Explicitly publish error for PLC communication issues
                    await self._message_broker.publish("error", {
                        "error": str(e),
                        "topic": "tag/get",
                        "tag": tag_name,
                        "timestamp": datetime.now().isoformat()
                    })
                    raise  # Re-raise to trigger outer error handler
                
            else:
                # Return cached value for non-PLC tags
                value = self._tag_values.get(tag_name)
                if value is None:
                    raise ValueError(f"Unknown tag: {tag_name}")
                
                await self._message_broker.publish(
                    "tag/get/response",
                    {
                        "tag": tag_name,
                        "value": value,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
        except Exception as e:
            logger.error(f"Error getting tag {tag_name}: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "topic": "tag/get",
                "tag": tag_name,
                "timestamp": datetime.now().isoformat()
            })

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