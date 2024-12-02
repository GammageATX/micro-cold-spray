import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, cast

from loguru import logger

from ...exceptions import HardwareError
from ...hardware.communication.plc_client import PLCClient
from ...hardware.communication.ssh_client import SSHClient
from ...infrastructure.config.config_manager import ConfigManager
from ..messaging.message_broker import MessageBroker


class TagManager:
    """
    Manages system tags and hardware communication.
    Single Source of Truth for all hardware interactions.
    """

    def __init__(self, message_broker: MessageBroker, config_manager: ConfigManager):
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
        self._shutdown = False  # Add shutdown flag

        logger.info("TagManager initialized")

    async def test_connections(self) -> Dict[str, bool]:
        """Test connections to all hardware clients."""
        results = {"plc": False, "feeder": False}

        # Test PLC connection
        if self._plc_client is not None:
            plc_client = cast(PLCClient, self._plc_client)
            try:
                # Test PLC by attempting to get tags
                await plc_client.get_all_tags()
                results["plc"] = True
            except Exception as e:
                logger.warning(f"PLC connection test failed: {str(e)}")
                results["plc"] = False

        # Test SSH connection
        if self._ssh_client is not None:
            ssh_client = cast(SSHClient, self._ssh_client)
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
            raise HardwareError(
                f"TagManager initialization failed: {
                    str(e)}",
                "tags",
            ) from e

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

            plc_client = cast(PLCClient, self._plc_client)
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
        """Handle tag set requests."""
        try:
            tag = data.get("tag")
            value = data.get("value")

            if not isinstance(tag, str):
                raise ValueError(f"Tag must be a string, got {type(tag)}")

            if tag in self._plc_tag_map:
                if self._plc_client is None:
                    raise RuntimeError("PLC client not initialized")

                plc_client = cast(PLCClient, self._plc_client)
                plc_tag = str(self._plc_tag_map[tag])
                await plc_client.write_tag(plc_tag, value)

        except Exception as e:
            error_msg = {
                "error": str(e),
                "context": "tag_set",
                "tag": data.get("tag"),
                "value": data.get("value"),
                "timestamp": datetime.now().isoformat(),
            }
            logger.error(f"Error setting tag: {error_msg}")
            await self._message_broker.publish("error", error_msg)

    async def _handle_tag_get(self, data: Dict[str, Any]) -> None:
        """Handle tag get requests."""
        try:
            tag = data.get("tag")
            if not isinstance(tag, str):
                raise ValueError(f"Tag must be a string, got {type(tag)}")

            if tag in self._plc_tag_map:
                if self._plc_client is None:
                    raise RuntimeError("PLC client not initialized")

                plc_client = cast(PLCClient, self._plc_client)
                plc_tag = str(self._plc_tag_map[tag])
                tags = await plc_client.get_all_tags()

                if plc_tag in tags:
                    await self._message_broker.publish(
                        "tag/get/response",
                        {
                            "tag": tag,
                            "value": tags[plc_tag],
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                else:
                    raise ValueError(f"Tag {plc_tag} not found in PLC tags")

        except Exception as e:
            logger.error(f"Error getting tag {tag}: {e}")
            await self._message_broker.publish(
                "error",
                {"error": str(e), "context": "tag_get", "timestamp": datetime.now().isoformat()},
            )

    async def shutdown(self) -> None:
        """Shutdown tag manager."""
        try:
            self._shutdown = True

            if self._polling_task:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass

            # No need to explicitly disconnect PLC - it's handled by the library
            if self._ssh_client is not None:
                try:
                    await self._ssh_client.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting SSH client: {e}")

            logger.info("TagManager shutdown complete")

        except Exception as e:
            logger.error(f"Error during TagManager shutdown: {e}")
            raise

    async def _write_tag(self, tag: str, value: Any) -> None:
        """Write tag value to hardware."""
        try:
            if not isinstance(tag, str):
                raise ValueError(f"Tag must be a string, got {type(tag)}")

            if tag in self._plc_tag_map:
                if self._plc_client is None:
                    raise RuntimeError("PLC client not initialized")

                plc_client = cast(PLCClient, self._plc_client)
                plc_tag = str(self._plc_tag_map[tag])  # Ensure string type
                await plc_client.write_tag(plc_tag, value)

        except Exception as e:
            error_msg = {
                "error": str(e),
                "context": "tag_set",
                "tag": tag,
                "value": value,
                "timestamp": datetime.now().isoformat(),
            }
            logger.error(f"Error setting tag: {error_msg}")
            await self._message_broker.publish("error", error_msg)

    async def _poll_hardware(self) -> None:
        """Poll hardware for updates."""
        try:
            while not self._shutdown:
                logger.debug("Polling hardware for updates")

                # Check PLC connection
                plc_connected = False
                if self._plc_client is not None:
                    plc_client = cast(PLCClient, self._plc_client)
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
                    ssh_client = cast(SSHClient, self._ssh_client)
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

            plc_client = cast(PLCClient, self._plc_client)
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

                plc_client = cast(PLCClient, self._plc_client)
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
