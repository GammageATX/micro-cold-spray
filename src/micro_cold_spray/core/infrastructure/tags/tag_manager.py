import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, cast

from loguru import logger

from ...exceptions import HardwareError
from ...hardware.communication import (
    create_plc_client, create_ssh_client,
    PLCClientType, SSHClientType
)
from ..config.config_manager import ConfigManager
from ..messaging.message_broker import MessageBroker


class TagManager:
    """
    Manages system tags and hardware communication.
    Single Source of Truth for all hardware interactions.
    """

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        test_mode: bool = False
    ) -> None:
        """Initialize with required dependencies."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._test_mode = test_mode

        # Hardware clients
        self._plc_client: Optional[PLCClientType] = None
        self._ssh_client: Optional[SSHClientType] = None

        # Tag management
        self._tag_config = {}  # Full tag configuration from tags.yaml
        self._tag_values: Dict[str, Any] = {}  # Current tag values
        self._plc_tag_map: Dict[str, str] = {}  # Maps system tags to PLC tags
        self._polling_task: Optional[asyncio.Task] = None
        self._is_initialized = False
        self._shutdown = False  # Add shutdown flag

        logger.info("TagManager initialized")

    async def initialize(self) -> None:
        """Initialize tag manager."""
        try:
            # Get hardware config
            hw_config = await self._config_manager.get_config("hardware")
            if not hw_config:
                raise HardwareError("No hardware configuration found", "tags")

            # Get application config to check mock_hardware setting
            app_config = await self._config_manager.get_config("application")
            app_section = app_config.get("application", {})
            dev_section = app_section.get("development", {})
            use_mock = dev_section.get("mock_hardware", False)
            logger.info(f"Using mock hardware: {use_mock}")

            # Initialize PLC client using factory
            if not self._plc_client:
                self._plc_client = create_plc_client(hw_config, use_mock)
                await self._plc_client.connect()

            # Initialize SSH client using factory
            if not self._ssh_client:
                self._ssh_client = create_ssh_client(hw_config, use_mock)
                await self._ssh_client.connect()

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
            raise HardwareError(
                f"TagManager initialization failed: {str(e)}",
                "tags",
            ) from e

    async def shutdown(self) -> None:
        """Shutdown tag manager."""
        try:
            self._shutdown = True

            # Cancel polling task
            if self._polling_task and not self._polling_task.done():
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass

            # Disconnect clients
            if self._ssh_client:
                await self._ssh_client.disconnect()

            if self._plc_client:
                await self._plc_client.disconnect()

            logger.info("TagManager shutdown complete")

        except Exception as e:
            logger.error(f"Error during TagManager shutdown: {e}")
            raise HardwareError("Failed to shutdown TagManager", "tags") from e

    async def test_connections(self) -> Dict[str, bool]:
        """Test connections to all hardware clients."""
        results = {"plc": False, "feeder": False}

        # Test PLC connection
        if self._plc_client is not None:
            plc_client = cast(PLCClientType, self._plc_client)
            try:
                # Test PLC by attempting to get tags
                await plc_client.get_all_tags()
                results["plc"] = True
            except Exception as e:
                logger.warning(f"PLC connection test failed: {str(e)}")
                results["plc"] = False

        # Test SSH connection
        if self._ssh_client is not None:
            ssh_client = cast(SSHClientType, self._ssh_client)
            try:
                # Test SSH connection
                await ssh_client.test_connection()
                results["feeder"] = True
            except Exception as e:
                logger.warning(f"SSH connection test failed: {str(e)}")
                results["feeder"] = False

        # Publish connection status
        for device, connected in results.items():
            await self._message_broker.publish(
                "tag/update",
                {
                    "tag": f"hardware.{device}.connected",
                    "value": connected,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        return results

    def _build_tag_maps(self) -> None:
        """Build mappings from tag configuration."""

        def process_group(group: Dict[str, Any], prefix: str = ""):
            for name, config in group.items():
                full_name = f"{prefix}.{name}" if prefix else name

                if isinstance(config, dict):
                    if config.get("mapped") and config.get("plc_tag"):
                        self._plc_tag_map[full_name] = config["plc_tag"]
                    elif "ssh" in config:
                        # SSH tags are handled directly
                        pass
                    elif not config.get("internal", False):
                        process_group(config, full_name)

        process_group(self._tag_config.get("tag_groups", {}))

    async def _poll_loop(self) -> None:
        """Poll hardware for updates."""
        try:
            while not self._shutdown:
                # Add debug logging
                logger.debug("Polling hardware for updates")

                # Get PLC status
                plc_connected = False
                if self._plc_client is not None:
                    try:
                        await self._plc_client.get_all_tags()
                        plc_connected = True
                    except Exception as e:
                        logger.warning(f"PLC connection error: {e}")
                        plc_connected = False
                        # Publish error
                        await self._message_broker.publish(
                            "error",
                            {
                                "error": str(e),
                                "source": "plc",
                                "context": "polling",
                                "timestamp": datetime.now().isoformat()
                            }
                        )

                await self._message_broker.publish(
                    "tag/update",
                    {
                        "tag": "hardware.plc.connected",
                        "value": plc_connected,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

                # Get SSH status
                ssh_connected = False
                if self._ssh_client is not None:
                    try:
                        ssh_connected = await self._ssh_client.test_connection()
                    except Exception as e:
                        logger.warning(f"SSH connection error: {e}")
                        ssh_connected = False
                        # Publish error
                        await self._message_broker.publish(
                            "error",
                            {
                                "error": str(e),
                                "source": "ssh",
                                "context": "polling",
                                "timestamp": datetime.now().isoformat()
                            }
                        )

                await self._message_broker.publish(
                    "tag/update",
                    {
                        "tag": "hardware.ssh.connected",
                        "value": ssh_connected,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

                # Publish combined hardware status
                await self._message_broker.publish(
                    "hardware/status",
                    {
                        "plc_connected": plc_connected,
                        "ssh_connected": ssh_connected,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

                # In test mode, break after one iteration
                if self._test_mode:
                    break

                await asyncio.sleep(1.0)  # Poll every second

        except Exception as e:
            logger.error(f"Error in polling loop: {e}")
            # Re-raise to allow proper error handling
            raise

    async def _poll_tags(self) -> None:
        """Poll PLC tags and publish updates."""
        try:
            if self._plc_client is None:
                return

            plc_client = cast(PLCClientType, self._plc_client)
            try:
                plc_tags = await plc_client.get_all_tags()
            except Exception as e:
                logger.warning(f"Failed to get PLC tags: {str(e)}")
                return

            # Update tag values and publish changes
            for system_tag, plc_tag in self._plc_tag_map.items():
                plc_tag_str = str(plc_tag)
                if plc_tag_str in plc_tags:
                    new_value = plc_tags[plc_tag_str]
                    has_tag = system_tag in self._tag_values
                    value_changed = has_tag and self._tag_values[system_tag] != new_value

                    if not has_tag or value_changed:
                        self._tag_values[system_tag] = new_value
                        await self._message_broker.publish(
                            "tag/update", {"tag": system_tag, "value": new_value}
                        )

        except Exception as e:
            error_msg = {
                "error": str(e),
                "context": "tag_polling",
                "timestamp": datetime.now().isoformat(),
            }
            await self._message_broker.publish("error", error_msg)
            raise HardwareError("Failed to poll tags", "plc", error_msg)

    async def _handle_tag_set(self, data: Dict[str, Any]) -> None:
        """Handle tag set messages."""
        try:
            tag = data.get("tag")
            value = data.get("value")
            if not tag or "value" not in data:
                raise ValueError("Missing tag or value in request")

            await self.write_tag(tag, value)

        except Exception as e:
            logger.error(f"Error handling tag set: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "source": "tags",
                    "error": str(e),
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _handle_tag_get(self, data: Dict[str, Any]) -> None:
        """Handle tag get messages."""
        try:
            tag = data.get("tag")
            if not tag:
                raise ValueError("Missing tag in request")

            # Get current value from cache
            value = self._tag_values.get(tag)

            # Publish response
            await self._message_broker.publish(
                "tag/get/response",
                {
                    "tag": tag,
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error handling tag get: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "source": "tags",
                    "error": str(e),
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Write a tag value to hardware."""
        try:
            # Parse tag path to determine hardware target
            parts = tag_name.split(".")
            if not parts:
                raise ValueError(f"Invalid tag name: {tag_name}")

            if parts[0] == "plc" and self._plc_client:
                # Get PLC tag address from config
                tag_config = self._tag_definitions.get("plc", {}).get(parts[1], {})
                if not tag_config:
                    raise ValueError(f"Tag not found in config: {tag_name}")

                address = tag_config.get("address")
                if not address:
                    raise ValueError(f"No address for tag: {tag_name}")

                await self._plc_client.write_tag(address, value)

                # Publish update
                await self._message_broker.publish(
                    "tag/update",
                    {
                        "tag": tag_name,
                        "value": value,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            elif parts[0] == "motion" and self._ssh_client:
                # Get motion command from config
                tag_config = self._tag_definitions.get("motion", {}).get(parts[1], {})
                if not tag_config:
                    raise ValueError(f"Tag not found in config: {tag_name}")

                command = tag_config.get("command", "").format(value=value)
                if not command:
                    raise ValueError(f"No command for tag: {tag_name}")

                await self._ssh_client.write_command(command)

                # Publish update
                await self._message_broker.publish(
                    "tag/update",
                    {
                        "tag": tag_name,
                        "value": value,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            else:
                raise ValueError(f"Unsupported tag type: {parts[0]}")

        except Exception as e:
            logger.error(f"Error writing tag {tag_name}: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "source": "tags",
                    "error": str(e),
                    "tag": tag_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise HardwareError(f"Failed to write tag {tag_name}: {str(e)}", "tags") from e

    async def _poll_hardware(self) -> None:
        """Poll hardware for updates."""
        try:
            while not self._shutdown:
                logger.debug("Polling hardware for updates")

                # Check PLC connection
                plc_connected = False
                if self._plc_client is not None:
                    plc_client = cast(PLCClientType, self._plc_client)
                    try:
                        # Test connection by attempting to get tags
                        await plc_client.get_all_tags()
                        plc_connected = True
                    except Exception as e:
                        logger.warning(f"PLC connection error: {str(e)}")
                        plc_connected = False

                await self._message_broker.publish(
                    "tag/update",
                    {
                        "tag": "hardware.plc.connected",
                        "value": plc_connected,
                        "timestamp": datetime.now().isoformat()
                    }
                )

                # Check SSH connection
                ssh_connected = False
                if self._ssh_client is not None:
                    ssh_client = cast(SSHClientType, self._ssh_client)
                    try:
                        await ssh_client.test_connection()
                        ssh_connected = True
                    except Exception as e:
                        logger.warning(f"SSH connection error: {str(e)}")
                        ssh_connected = False

                await self._message_broker.publish(
                    "tag/update",
                    {
                        "tag": "hardware.ssh.connected",
                        "value": ssh_connected,
                        "timestamp": datetime.now().isoformat()
                    }
                )

                await asyncio.sleep(1)

        except Exception as e:
            logger.exception(f"Error polling hardware: {str(e)}")

    async def _poll_plc(self) -> None:
        """Poll PLC for tag updates."""
        try:
            if self._plc_client is None:
                logger.warning("PLC client not initialized")
                return

            plc_client = cast(PLCClientType, self._plc_client)
            try:
                plc_tags = await plc_client.get_all_tags()
            except Exception as e:
                logger.warning(f"Failed to get PLC tags: {str(e)}")
                return

            # Update tag values and publish changes
            for system_tag, plc_tag in self._plc_tag_map.items():
                plc_tag_str = str(plc_tag)
                if plc_tag_str in plc_tags:
                    new_value = plc_tags[plc_tag_str]
                    has_tag = system_tag in self._tag_values
                    value_changed = has_tag and self._tag_values[system_tag] != new_value

                    if not has_tag or value_changed:
                        self._tag_values[system_tag] = new_value
                        await self._message_broker.publish(
                            "tag/update", {"tag": system_tag, "value": new_value}
                        )

        except Exception as e:
            logger.exception(f"Error polling PLC tags: {str(e)}")

    async def _handle_get_request(self, data: Dict[str, Any]) -> None:
        """Handle tag get request."""
        try:
            if not isinstance(data, dict) or "tag" not in data:
                raise ValueError("Invalid tag get request format")

            tag = data.get("tag")
            if not isinstance(tag, str):
                raise ValueError(f"Tag must be a string, got {type(tag)}")

            if tag in self._plc_tag_map:
                if self._plc_client is None:
                    raise RuntimeError("PLC client not initialized")

                plc_client = cast(PLCClientType, self._plc_client)
                plc_tag = str(self._plc_tag_map[tag])
                tags = await plc_client.get_all_tags()
                if plc_tag in tags:
                    value = tags[plc_tag]
                    await self._message_broker.publish(
                        "tag/get/response",
                        {"tag": tag, "value": value, "timestamp": datetime.now().isoformat()},
                    )
                else:
                    raise ValueError(f"Tag {plc_tag} not found in PLC tags")

        except Exception as e:
            logger.error(f"Error getting tag {tag}: {e}")
            await self._message_broker.publish(
                "error",
                {"error": str(e), "context": "tag_get", "timestamp": datetime.now().isoformat()},
            )
