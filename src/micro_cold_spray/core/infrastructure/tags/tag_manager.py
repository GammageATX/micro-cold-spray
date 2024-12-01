from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from datetime import datetime

from ...exceptions import HardwareError
from ...exceptions import ValidationError

from ..messaging.message_broker import MessageBroker
from ...infrastructure.config.config_manager import ConfigManager
from ...hardware.communication.plc_client import PLCClient
from ...hardware.communication.ssh_client import SSHClient
from ...exceptions import HardwareError

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
        """Test connections to all hardware clients."""
        results = {
            "plc": False,
            "feeder": False
        }
        
        # Test PLC connection
        if self._plc_client:
            results["plc"] = await self._plc_client.test_connection()
        
        # Test SSH connection
        if self._ssh_client:
            results["feeder"] = await self._ssh_client.test_connection()
        
        # Publish connection status
        for device, connected in results.items():
            await self._message_broker.publish("tag/update", {
                "tag": f"hardware.{device}.connected",
                "value": connected,
                "timestamp": datetime.now().isoformat()
            })
        
        return results

    async def initialize(self) -> None:
        """Initialize tag manager."""
        try:
            # Get hardware config
            hw_config = await self._config_manager.get_config("hardware")
            if not hw_config:
                raise HardwareError("No hardware configuration found", "tags")

            # Initialize PLC client
            if not self._plc_client:
                self._plc_client = PLCClient(hw_config)
            
            # Initialize SSH client
            if not self._ssh_client:
                self._ssh_client = SSHClient(hw_config)
            
            # Initialize tag definitions
            tag_config = await self._config_manager.get_config("tags")
            if not tag_config:
                raise HardwareError("No tag configuration found", "tags")
            
            self._tag_definitions = tag_config.get("groups", {})
            
            # Subscribe to tag messages
            await self._message_broker.subscribe("tag/set", self._handle_tag_set)
            await self._message_broker.subscribe("tag/get", self._handle_tag_get)
            
            # Start polling loop
            self._polling_task = asyncio.create_task(self._poll_loop())
            
            self._is_initialized = True
            logger.info("TagManager initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize TagManager: {e}")
            raise HardwareError(f"TagManager initialization failed: {str(e)}", "tags") from e

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

    async def _poll_loop(self) -> None:
        """Poll hardware for updates."""
        try:
            while not self._shutdown:
                # Add debug logging
                logger.debug("Polling hardware for updates")
                
                # Get PLC status
                plc_connected = await self._plc_client.test_connection()
                await self._message_broker.publish(
                    "tag/update",
                    {
                        "tag": "hardware.plc.connected",
                        "value": plc_connected,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                # Get SSH status  
                ssh_connected = await self._ssh_client.test_connection()
                await self._message_broker.publish(
                    "tag/update", 
                    {
                        "tag": "hardware.ssh.connected",
                        "value": ssh_connected,
                        "timestamp": datetime.now().isoformat()
                    }
                )

                # Publish combined hardware status
                await self._message_broker.publish(
                    "hardware/status",
                    {
                        "plc_connected": plc_connected,
                        "ssh_connected": ssh_connected,
                        "timestamp": datetime.now().isoformat()
                    }
                )

                await asyncio.sleep(1.0)  # Poll every second
                
        except Exception as e:
            logger.error(f"Error in polling loop: {e}")

    async def _poll_tags(self) -> None:
        """Poll PLC tags and publish updates."""
        try:
            # Skip polling if not connected
            if not self._plc_client._connected:
                return
            
            # Get all PLC tags
            plc_tags = await self._plc_client.get_all_tags()
            
            # Update tag values and publish changes
            for system_tag, plc_tag in self._plc_tag_map.items():
                if plc_tag in plc_tags:
                    new_value = plc_tags[plc_tag]
                    if system_tag not in self._tag_values or self._tag_values[system_tag] != new_value:
                        self._tag_values[system_tag] = new_value
                        await self._message_broker.publish("tag/update", {
                            "tag": system_tag,
                            "value": new_value,
                            "timestamp": datetime.now().isoformat()
                        })
                    
        except Exception as e:
            error_msg = {
                "error": str(e),
                "context": "tag_polling",
                "timestamp": datetime.now().isoformat()
            }
            await self._message_broker.publish("error", error_msg)
            raise HardwareError("Failed to poll tags", "plc", error_msg)

    async def _handle_tag_set(self, data: Dict[str, Any]) -> None:
        """Handle tag set requests."""
        try:
            tag = data.get("tag")
            value = data.get("value")
            
            if tag in self._plc_tag_map:
                plc_tag = self._plc_tag_map[tag]
                await self._plc_client.write_tag(plc_tag, value)
                
        except Exception as e:
            error_msg = {
                "error": str(e),
                "context": "tag_set",
                "tag": data.get("tag"),
                "value": data.get("value"),
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error setting tag: {error_msg}")
            await self._message_broker.publish("error", error_msg)

    async def _handle_tag_get(self, data: Dict[str, Any]) -> None:
        """Handle tag get requests."""
        try:
            tag = data.get("tag")
            if tag in self._plc_tag_map:
                plc_tag = self._plc_tag_map[tag]
                value = await self._plc_client.get_all_tags()
                
                await self._message_broker.publish("tag/get/response", {
                    "tag": tag,
                    "value": value.get(plc_tag),
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error getting tag {tag}: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "context": "tag_get",
                "timestamp": datetime.now().isoformat()
            })

    async def shutdown(self) -> None:
        """Shutdown tag manager."""
        try:
            # Set flag to stop polling loop
            self._is_initialized = False
            
            # Cancel polling task first
            if self._polling_task and not self._polling_task.done():
                self._polling_task.cancel()
                try:
                    # Wait for task to complete with timeout
                    await asyncio.wait_for(self._polling_task, timeout=0.5)
                except asyncio.TimeoutError:
                    logger.warning("Polling task shutdown timed out")
                except asyncio.CancelledError:
                    logger.debug("Polling task cancelled")
                except Exception as e:
                    logger.error(f"Error during polling task shutdown: {e}")

            # Disconnect hardware clients
            if self._plc_client:
                try:
                    await self._plc_client.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting PLC client: {e}")

            if self._ssh_client:
                try:
                    await self._ssh_client.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting SSH client: {e}")

            logger.info("TagManager shutdown complete")

        except Exception as e:
            logger.exception("Error during TagManager shutdown")
            raise HardwareError(f"TagManager shutdown failed: {str(e)}", "tags") from e