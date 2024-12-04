"""State Manager module."""
from datetime import datetime
from typing import Dict, Any
from loguru import logger

from micro_cold_spray.core.exceptions import StateError
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager


class StateManager:
    """Manages system state transitions and conditions."""

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager
    ) -> None:
        """Initialize state manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._state_config = {}
        self._current_state = None
        self._previous_state = ""
        self._conditions = {}
        self._is_initialized = False
        logger.info("State manager initialized")

    async def initialize(self) -> None:
        """Initialize state manager subscriptions."""
        try:
            # Subscribe to state requests and tag updates
            await self._message_broker.subscribe("state/request", self._handle_state_request)
            await self._message_broker.subscribe("tag/update", self._handle_tag_update)

            # Load state config from state.yaml
            config = await self._config_manager.get_config("state")
            self._state_config = config.get("state", {}).get("transitions", {})

            # Set initial state from config
            self._current_state = config.get("state", {}).get("initial_state", "INITIALIZING")
            self._previous_state = ""
            logger.debug(f"Loaded state transitions: {self._state_config}")
            logger.debug(f"Initial state set to: {self._current_state}")

            # Initialize condition tracking
            self._conditions = {
                "hardware.connected": False,
                "config.loaded": True,  # Set by ConfigManager
                "hardware.enabled": False,
                "sequence.active": False,
                "hardware.safe": True  # Default to safe
            }

            # Subscribe to hardware status
            await self._message_broker.subscribe(
                "hardware/status/plc",
                self._handle_hardware_status
            )
            await self._message_broker.subscribe(
                "hardware/status/motion",
                self._handle_hardware_status
            )

            self._is_initialized = True
            logger.info("State manager initialization complete")

        except Exception as e:
            logger.exception("Failed to initialize state manager")
            raise StateError(
                f"State manager initialization failed: {str(e)}") from e

    async def _handle_state_request(self, data: Dict[str, Any]) -> None:
        """Handle state change request."""
        try:
            requested_state = data.get("state")
            if not requested_state:
                raise StateError("No state specified in request")

            # Get current state config
            current_state_config = self._state_config.get(self._current_state, {})
            valid_transitions = current_state_config.get("next_states", [])

            # Check if transition is valid
            if requested_state in valid_transitions:
                # Get required conditions for requested state
                required_conditions = self._state_config.get(
                    requested_state, {}).get("conditions", [])

                # Check if conditions are met
                conditions_met = all(
                    self._conditions.get(condition, False)
                    for condition in required_conditions
                )

                if conditions_met or requested_state == "ERROR":
                    # Perform state transition
                    self._previous_state = self._current_state
                    self._current_state = requested_state

                    # Publish state change
                    change_data = {
                        "state": requested_state,
                        "previous": self._previous_state,
                        "description": self._state_config.get(requested_state, {}).get("description", ""),
                        "timestamp": datetime.now().isoformat()
                    }

                    if "error" in data:
                        change_data["error"] = data["error"]

                    await self._message_broker.publish(
                        "state/change",
                        change_data
                    )
                    logger.info(
                        f"State changed from {
                            self._previous_state} to {requested_state}")

                else:
                    error_msg = f"Required conditions not met for {requested_state}"
                    logger.error(error_msg)
                    await self._message_broker.publish("error", {
                        "error": error_msg,
                        "topic": "state/transition",
                        "context": "state_conditions",
                        "timestamp": datetime.now().isoformat()
                    })

            else:
                error_msg = f"Invalid state transition from {
                    self._current_state} to {requested_state}"
                logger.error(error_msg)
                await self._message_broker.publish("error", {
                    "error": error_msg,
                    "topic": "state/transition",
                    "context": "state_transition",
                    "timestamp": datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"Error handling state request: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "topic": "state/request",
                "context": "state_request",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle tag updates that affect state conditions."""
        try:
            tag = data.get("tag")
            value = data.get("value")

            # Skip if tag or value is None
            if tag is None or value is None:
                return

            # Map tag updates to conditions
            condition_map = {
                "hardware.plc.connected": "hardware.connected",
                "hardware.motion.connected": "hardware.connected",
                "hardware.plc.enabled": "hardware.enabled",
                "hardware.motion.enabled": "hardware.enabled",
                "sequence.active": "sequence.active",
                "hardware.safe": "hardware.safe"
            }

            if tag in condition_map:
                condition = condition_map[tag]
                # Convert value to bool to ensure type safety
                self._conditions[condition] = bool(value)
                logger.debug(f"Updated condition {condition}: {value}")

        except Exception as e:
            logger.error(f"Error handling tag update: {e}")

    async def _handle_hardware_status(self, data: Dict[str, Any]) -> None:
        """Handle hardware status updates."""
        try:
            status = data.get("status")
            if status == "connected":
                self._conditions["hardware.connected"] = True
            elif status == "disconnected":
                self._conditions["hardware.connected"] = False

            logger.debug(
                f"Updated hardware connection status: {
                    self._conditions['hardware.connected']}")

        except Exception as e:
            logger.error(f"Error handling hardware status: {e}")

    async def shutdown(self) -> None:
        """Shutdown state manager."""
        try:
            # Unsubscribe from topics with their handlers
            topics_and_handlers = [
                ("state/request", self._handle_state_request),
                ("tag/update", self._handle_tag_update),
                ("hardware/status/plc", self._handle_hardware_status),
                ("hardware/status/motion", self._handle_hardware_status)
            ]

            for topic, handler in topics_and_handlers:
                await self._message_broker.unsubscribe(topic, handler)

            logger.info("State manager shutdown complete")

        except Exception as e:
            logger.error(f"Error during state manager shutdown: {e}")
