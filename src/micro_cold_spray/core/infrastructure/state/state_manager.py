"""State Manager component.

Manages system state according to state.yaml:
- State transitions
- State validation
- State error handling
- Message pattern compliance
"""
from datetime import datetime
from typing import Any, Dict
from loguru import logger
from micro_cold_spray.core.exceptions import StateError
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker


class StateManager:
    """Manages system state transitions."""

    def __init__(
            self,
            message_broker: MessageBroker,
            config_manager: ConfigManager):
        """Initialize state manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._current_state = "INITIALIZING"
        self._previous_state = ""
        self._hardware_ready = False
        self._motion_ready = False
        logger.info("State manager initialized")

    async def initialize(self) -> None:
        """Initialize state manager subscriptions."""
        try:
            # Subscribe to state requests and tag updates
            await self._message_broker.subscribe("state/request", self._handle_state_request)
            await self._message_broker.subscribe("tag/update", self._handle_tag_update)

            # Load state config directly from state.yaml
            config = await self._config_manager.get_config("state")
            self._state_config = config.get("transitions", {})
            logger.debug(f"Loaded state transitions: {self._state_config}")

            # Start in INITIALIZING state
            self._current_state = "INITIALIZING"
            self._previous_state = ""

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

            logger.info("State manager initialization complete")

        except Exception as e:
            logger.exception("Failed to initialize state manager")
            raise StateError(
                f"State manager initialization failed: {
                    str(e)}") from e

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle tag updates and check conditions."""
        try:
            tag = data.get("tag")
            value = data.get("value")
            logger.debug(f"Handling tag update: {tag} = {value}")

            # Update condition based on tag
            if tag == "hardware.connected":
                if not isinstance(value, bool):
                    logger.warning(f"Invalid value type for hardware.connected: {type(value)}")
                    return
                self._conditions["hardware.connected"] = value
                logger.debug(f"Updated hardware.connected to {value}")
                await self._check_conditions()

            elif tag == "hardware.enabled":
                if not isinstance(value, bool):
                    logger.warning(f"Invalid value type for hardware.enabled: {type(value)}")
                    return
                self._conditions["hardware.enabled"] = value
                logger.debug(f"Updated hardware.enabled to {value}")
                await self._check_conditions()

            elif tag == "sequence.active":
                if not isinstance(value, bool):
                    logger.warning(f"Invalid value type for sequence.active: {type(value)}")
                    return
                self._conditions["sequence.active"] = value
                logger.debug(f"Updated sequence.active to {value}")
                await self._check_conditions()

        except Exception as e:
            logger.error(f"Error handling tag update: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "topic": "tag/update",
                "context": "tag_update",
                "timestamp": datetime.now().isoformat()
            })

    async def _check_conditions(self) -> None:
        """Check if conditions are met for state transition."""
        try:
            logger.debug(f"Checking conditions: {self._conditions}")

            # Check INITIALIZING -> READY transition
            if self._current_state == "INITIALIZING":
                if self._conditions.get(
                        "hardware.connected") and self._conditions.get("config.loaded"):
                    logger.debug("Conditions met for READY transition")
                    # Directly set state since we are the state manager
                    await self.set_state("READY")

        except Exception as e:
            logger.error(f"Error checking conditions: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "topic": "state/conditions",
                "context": "condition_check",
                "timestamp": datetime.now().isoformat()
            })

    async def set_state(self, new_state: str) -> None:
        """Set system state and publish change."""
        try:
            if not self._is_valid_transition(new_state):
                error_msg = {
                    "error": f"Invalid state transition from {
                        self._current_state} to {new_state}",
                    "context": "state_transition",
                    "current_state": self._current_state,
                    "requested_state": new_state,
                    "timestamp": datetime.now().isoformat()}
                await self._message_broker.publish("error", error_msg)
                raise StateError("Invalid state transition", error_msg)

            # Update state
            self._previous_state = self._current_state
            self._current_state = new_state

            await self._message_broker.publish(
                "state/change",
                {
                    "state": new_state,
                    "previous": self._previous_state,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            error_msg = {
                "error": str(e),
                "context": "state_transition",
                "current_state": self._current_state,
                "requested_state": new_state,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error setting state: {error_msg}")
            await self._message_broker.publish("error", error_msg)
            raise

    async def _handle_state_request(self, data: Dict[str, Any]) -> None:
        """Handle state change requests."""
        try:
            # Check both keys for compatibility
            requested_state = data.get("state") or data.get("requested_state")
            logger.debug(f"Handling state request: {requested_state}")

            if not requested_state:
                error_msg = f"Invalid state request - no state specified: {data}"
                logger.error(error_msg)
                await self._message_broker.publish("error", {
                    "error": error_msg,
                    "topic": "state/request",
                    "context": "state_request",
                    "timestamp": datetime.now().isoformat()
                })
                return

            # Get current state config
            current_state_config = self._state_config.get(
                self._current_state, {})
            valid_transitions = current_state_config.get("next_states", [])
            required_conditions = current_state_config.get("conditions", [])

            # Check if transition is valid and conditions are met
            if requested_state in valid_transitions:
                # Check conditions
                conditions_met = all(self._conditions.get(cond, False)
                                     for cond in required_conditions)

                if conditions_met:
                    # Update state
                    self._previous_state = self._current_state
                    self._current_state = requested_state

                    # Publish state change
                    await self._message_broker.publish("state/change", {
                        "state": self._current_state,
                        "previous": self._previous_state,
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.info(
                        f"State changed from {
                            self._previous_state} to {
                            self._current_state}")
                else:
                    error_msg = f"Conditions not met for transition to {requested_state}"
                    logger.error(error_msg)
                    await self._message_broker.publish("error", {
                        "error": error_msg,
                        "topic": "state/transition",
                        "context": "state_transition",
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

    def _is_valid_transition(self, new_state: str) -> bool:
        """Check if state transition is valid."""
        # Use cached state config
        current_state_config = self._state_config.get(self._current_state, {})
        valid_transitions = current_state_config.get("next_states", [])
        return new_state in valid_transitions

    async def get_current_state(self) -> str:
        """Get current state."""
        return self._current_state

    async def get_previous_state(self) -> str:
        """Get previous state."""
        return self._previous_state

    async def shutdown(self) -> None:
        """Shutdown state manager."""
        try:
            await self._message_broker.unsubscribe("state/request", self._handle_state_request)
            await self._message_broker.unsubscribe("tag/update", self._handle_tag_update)
            logger.info("State manager shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise

    async def _handle_hardware_status(self, data: Dict[str, Any]) -> None:
        """Handle hardware status updates."""
        try:
            # Update hardware status
            if "connected" in data:
                # Get topic from data
                if "source" in data and data["source"] == "plc":
                    self._conditions["hardware.connected"] = data["connected"]

                # Check if we should transition to READY
                if (self._current_state == "INITIALIZING"
                        and self._conditions.get("hardware.connected")
                        and self._conditions.get("config.loaded")):

                    # Update state
                    self._previous_state = self._current_state
                    self._current_state = "READY"

                    # Publish state change
                    await self._message_broker.publish(
                        "state/change",
                        {
                            "state": self._current_state,
                            "previous": self._previous_state,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    logger.info(
                        f"State changed from {
                            self._previous_state} to {
                            self._current_state}")

        except Exception as e:
            logger.error(f"Error handling hardware status: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "error": str(e),
                    "topic": "hardware/status",
                    "context": "hardware_status",
                    "timestamp": datetime.now().isoformat()
                }
            )
