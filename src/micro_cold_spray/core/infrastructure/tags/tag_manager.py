"""Tag Manager module for handling hardware communication and tag state."""
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from ...exceptions import HardwareError
from ...hardware.clients import (
    PLCClient,
    SSHClient,
    create_plc_client,
    create_ssh_client
)
from ..config.config_manager import ConfigManager
from ..messaging.message_broker import MessageBroker


class TagManager:
    """Manages hardware communication and tag state."""

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        test_mode: bool = False
    ) -> None:
        """Initialize tag manager."""
        # Dependencies
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._test_mode = test_mode

        # Hardware clients
        self._plc_client: Optional[PLCClient] = None
        self._ssh_client: Optional[SSHClient] = None

        # Tag management
        self._tag_definitions: Dict[str, Any] = {}
        self._plc_tag_map: Dict[str, str] = {}
        self._tag_values: Dict[str, Any] = {}

        # State
        self._is_initialized = False
        self._shutdown = False
        self._mock_mode = False
        self._polling_task = None

        logger.info("TagManager initialized")

    async def initialize(self) -> None:
        """Initialize tag manager."""
        try:
            # Get mock mode setting first
            app_config = await self._config_manager.get_config('application')
            self._mock_mode = app_config.get('development', {}).get('mock_hardware', False) or self._test_mode
            logger.info(f"Using mock hardware: {self._mock_mode}")

            # Get tag config
            tag_config = await self._config_manager.get_config('tags')
            self._tag_definitions = tag_config.get('tag_groups', {})
            if not self._tag_definitions:
                raise HardwareError("No tag groups defined in config", "tags")
            logger.debug(f"Tag config received with {len(self._tag_definitions)} groups")

            # Build PLC tag mapping first
            self._build_plc_tag_map()

            # Initialize hardware clients
            if self._mock_mode:
                # Create mock clients with empty config
                logger.info("Creating mock hardware clients")
                self._plc_client = create_plc_client({}, use_mock=True)
                self._ssh_client = create_ssh_client({}, use_mock=True)
            else:
                # Get hardware config and create real clients
                logger.info("Creating real hardware clients")
                hardware_config = await self._config_manager.get_config('hardware')
                logger.debug(f"Hardware config received: {hardware_config}")

                # Validate hardware config
                if not hardware_config.get('network', {}).get('plc'):
                    raise HardwareError("No PLC configuration found", "plc")
                if not hardware_config.get('network', {}).get('ssh'):
                    raise HardwareError("No SSH configuration found", "ssh")

                self._plc_client = create_plc_client({'hardware': hardware_config})
                self._ssh_client = create_ssh_client({'hardware': hardware_config})

            # Connect clients
            try:
                await self._plc_client.connect()
                await self._ssh_client.connect()
                await self._publish_hardware_state("plc", "connected")
                await self._publish_hardware_state("motion", "connected")
            except Exception as e:
                error_msg = f"Failed to connect to hardware: {str(e)}"
                logger.error(error_msg)
                if not self._mock_mode:
                    raise HardwareError(error_msg, "hardware") from e
                else:
                    logger.warning("Connection failed in mock mode - continuing anyway")

            # Subscribe to tag messages
            await self._message_broker.subscribe("tag/request", self._handle_tag_request)

            # Start polling loop
            self._polling_task = asyncio.create_task(self._poll_loop())

            self._is_initialized = True
            logger.info("TagManager initialization complete")

        except Exception as e:
            error_msg = f"Failed to initialize TagManager: {str(e)}"
            logger.error(error_msg)
            await self._publish_hardware_state("tags", "error", str(e))
            raise HardwareError(error_msg, "tags") from e

    def _build_plc_tag_map(self) -> None:
        """Build mapping between tag paths and PLC tags."""
        for group_name, group_data in self._tag_definitions.items():
            for tag_name, tag_data in group_data.get('tags', {}).items():
                tag_path = f"{group_name}/{tag_name}"
                plc_tag = tag_data.get('plc_tag', '')
                if plc_tag:
                    self._plc_tag_map[tag_path] = plc_tag
                    # Initialize mock value
                    if self._mock_mode:
                        self._tag_values[tag_path] = tag_data.get('default', 0)

    async def _publish_hardware_state(self, device: str, state: str, error: str = "") -> None:
        """Publish hardware state update."""
        await self._message_broker.publish(
            "hardware/state",
            {
                "device": device,
                "state": state,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        )

    async def _handle_tag_request(self, data: Dict[str, Any]) -> None:
        """Handle tag request messages."""
        request_id = data.get("request_id", "")
        try:
            request_type = data.get("request_type")
            tag_name = data.get("tag")
            if not request_type:
                await self._send_error("Missing request_type", request_id)
                return

            if not tag_name:
                await self._send_error("Missing tag name", request_id)
                return

            response_data = {
                "request_id": request_id,
                "tag": tag_name,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }

            if request_type == "get":
                value = await self.read_tag(tag_name)
                response_data["value"] = value

            elif request_type == "set":
                value = data.get("value")
                if value is None:
                    await self._send_error("Missing value", request_id)
                    return

                await self.write_tag(tag_name, value)
                response_data["value"] = value

            else:
                await self._send_error(f"Invalid request_type: {request_type}", request_id)
                return

            await self._message_broker.publish("tag/response", response_data)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error handling tag request: {error_msg}")
            await self._send_error(error_msg, request_id, tag_name)

    async def _send_error(self, error_msg: str, request_id: str, tag_name: str = None) -> None:
        """Send error response."""
        error_context = {
            "source": "tag_manager",
            "error": error_msg,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }
        if tag_name:
            error_context["tag"] = tag_name

        # Send to error topic
        await self._message_broker.publish("error", error_context)

        # Send error response
        response_data = {
            "success": False,
            "error": error_msg,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }
        if tag_name:
            response_data["tag"] = tag_name

        await self._message_broker.publish("tag/response", response_data)

    async def _poll_loop(self) -> None:
        """Poll hardware for tag updates."""
        try:
            while True:
                if not self._mock_mode:
                    # Only poll hardware in non-mock mode
                    for tag_path, plc_tag in self._plc_tag_map.items():
                        try:
                            value = await self._plc_client.read_tag(plc_tag)
                            if tag_path not in self._tag_values or value != self._tag_values[tag_path]:
                                self._tag_values[tag_path] = value
                                await self._message_broker.publish(
                                    "tag/update",
                                    {
                                        "tag": tag_path,
                                        "value": value,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Failed to read tag {tag_path}: {str(e)}")
                            await self._publish_hardware_state("plc", "error", str(e))

                await asyncio.sleep(1.0)  # Poll interval

        except asyncio.CancelledError:
            logger.debug("Tag polling cancelled")
        except Exception as e:
            logger.error(f"Tag polling error: {str(e)}")
            await self._publish_hardware_state("plc", "error", str(e))

    async def read_tag(self, tag_path: str) -> Any:
        """Read a tag value."""
        try:
            if tag_path not in self._plc_tag_map:
                raise ValueError(f"Tag not found in config: {tag_path}")

            if self._mock_mode:
                return self._tag_values.get(tag_path, 0)

            plc_tag = self._plc_tag_map[tag_path]
            value = await self._plc_client.read_tag(plc_tag)
            logger.debug(f"Read tag {tag_path} = {value}")
            return value

        except Exception as e:
            error_msg = f"Failed to read tag {tag_path}: {str(e)}"
            logger.error(error_msg)
            raise HardwareError(error_msg, "tags") from e

    async def write_tag(self, tag_path: str, value: Any) -> None:
        """Write a tag value."""
        try:
            if tag_path not in self._plc_tag_map:
                raise ValueError(f"Tag not found in config: {tag_path}")

            if self._mock_mode:
                if hasattr(self, '_plc_client') and self._plc_client is not None:
                    # If we have a mock PLC client, use it for error simulation
                    await self._plc_client.write_tag(self._plc_tag_map[tag_path], value)

                logger.debug(f"Mock write tag {tag_path} = {value}")
                # In mock mode, store the value and publish update
                self._tag_values[tag_path] = value
                await self._message_broker.publish(
                    "tag/update",
                    {
                        "tag": tag_path,
                        "value": value,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            plc_tag = self._plc_tag_map[tag_path]
            await self._plc_client.write_tag(plc_tag, value)
            logger.debug(f"Wrote tag {tag_path} = {value}")

            # Publish update
            await self._message_broker.publish(
                "tag/update",
                {
                    "tag": tag_path,
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            error_msg = f"Failed to write tag {tag_path}: {str(e)}"
            logger.error(error_msg)
            # Publish to both error and hardware/state topics
            await self._message_broker.publish(
                "error",
                {
                    "source": "tag_manager",
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
            )
            await self._publish_hardware_state("plc", "error", str(e))
            raise HardwareError(error_msg, "tags") from e

    async def shutdown(self) -> None:
        """Shutdown tag manager."""
        try:
            self._shutdown = True

            if self._polling_task and not self._polling_task.done():
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass

            if self._ssh_client:
                await self._ssh_client.disconnect()
                await self._publish_hardware_state("motion", "disconnected")

            if self._plc_client:
                await self._plc_client.disconnect()
                await self._publish_hardware_state("plc", "disconnected")

            logger.info("TagManager shutdown complete")

        except Exception as e:
            error_msg = f"Error during TagManager shutdown: {str(e)}"
            logger.error(error_msg)
            await self._publish_hardware_state("error", error_msg)
            raise HardwareError(error_msg, "tags")

    async def _create_plc_client(self, config: Dict[str, Any]) -> PLCClient:
        """Create PLC client instance."""
        try:
            from ...hardware.clients import PLCClient
            client = PLCClient({'hardware': {'network': {'plc': config}}})
            await client.connect()
            return client
        except Exception as e:
            error_msg = f"Failed to create PLC client: {str(e)}"
            logger.error(error_msg)
            await self._publish_hardware_state("plc", "error", error_msg)
            raise HardwareError(error_msg, "plc") from e

    async def _create_ssh_client(self, config: Dict[str, Any]) -> SSHClient:
        """Create SSH client instance."""
        try:
            from ...hardware.clients import SSHClient
            client = SSHClient(
                host=config.get("host", ""),
                port=config.get("port", 22),
                username=config.get("username", ""),
                password=config.get("password", "")
            )
            await client.connect()
            return client
        except Exception as e:
            error_msg = f"Failed to create SSH client: {str(e)}"
            logger.error(error_msg)
            await self._publish_hardware_state("motion", "error", error_msg)
            raise HardwareError(error_msg, "motion") from e

    async def _handle_hardware_status(self, data: Dict[str, Any]) -> None:
        """Handle hardware status updates."""
        try:
            device = data.get("device")
            status = data.get("status")

            if not device or not status:
                logger.warning("Invalid hardware status update", extra={"data": data})
                return

            # Map status to conditions
            if status == "connected":
                await self._publish_hardware_state(device, "connected")
            elif status == "disconnected":
                await self._publish_hardware_state(device, "disconnected")
            elif status == "error":
                await self._publish_hardware_state(device, "error", data.get("error", ""))

        except Exception as e:
            logger.error(f"Error handling hardware status: {e}")
            await self._publish_hardware_state("error", str(e))
