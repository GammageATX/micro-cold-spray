"""State Manager module."""
from datetime import datetime
from typing import Dict, Any, Set
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
        self._valid_states: Set[str] = set()
        self._is_initialized = False
        logger.info("State manager initialized")

    async def initialize(self) -> None:
        """Initialize state manager subscriptions."""
        try:
            if self._is_initialized:
                logger.warning("State manager already initialized")
                return

            # Load state config from state.yaml
            config = await self._config_manager.get_config("state")
            self._state_config = config.get("state", {}).get("transitions", {})
            self._valid_states = set(self._state_config.keys())

            # Validate state configuration
            if not self._valid_states:
                raise StateError("No valid states defined in configuration")

            # Set initial state from config
            initial_state = config.get("state", {}).get("initial_state")
            if initial_state not in self._valid_states:
                raise StateError(
                    "Invalid initial state",
                    {"initial_state": initial_state, "valid_states": list(self._valid_states)}
                )

            self._current_state = initial_state
            self._previous_state = ""
            logger.debug(f"Loaded state transitions: {self._state_config}")
            logger.debug(f"Initial state set to: {self._current_state}")

            # Initialize condition tracking
            self._conditions = {
                "hardware.connected": False,
                "hardware.plc.connected": False,
                "hardware.motion.connected": False,
                "config.loaded": True,  # Set by ConfigManager
                "hardware.enabled": False,
                "hardware.plc.enabled": False,
                "hardware.motion.enabled": False,
                "sequence.active": False,
                "hardware.safe": True  # Default to safe
            }

            # Subscribe to state requests and tag updates
            await self._message_broker.subscribe("state/request", self._handle_state_request)
            await self._message_broker.subscribe("tag/update", self._handle_tag_update)

            # Subscribe to hardware state
            await self._message_broker.subscribe("hardware/state", self._handle_hardware_status)

            self._is_initialized = True
            logger.info("State manager initialization complete")

        except Exception as e:
            error_context = {
                "source": "state_manager",
                "error": str(e),
                "context": {
                    "config": self._state_config if hasattr(self, '_state_config') else None,
                    "valid_states": list(self._valid_states) if hasattr(self, '_valid_states') else None
                },
                "timestamp": datetime.now().isoformat()
            }
            logger.error("Failed to initialize state manager", extra=error_context)
            await self._message_broker.publish("error", error_context)
            raise StateError("Failed to initialize state manager") from e

    async def _handle_state_request(self, data: Dict[str, Any]) -> None:
        """Handle state request messages."""
        try:
            request_type = data.get("request_type", "change")  # Default to change for backward compatibility
            request_id = data.get("request_id", "")
            requested_state = data.get("state")

            if not requested_state:
                raise StateError("No state specified in request")

            response_data = {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }

            if request_type == "change":
                # Validate requested state
                if requested_state not in self._valid_states:
                    raise StateError(
                        "Invalid state requested",
                        {"requested_state": requested_state, "valid_states": list(self._valid_states)}
                    )

                # Get current state config
                current_state_config = self._state_config.get(self._current_state, {})
                valid_transitions = current_state_config.get("next_states", [])

                # Check if transition is valid
                if requested_state in valid_transitions:
                    # Get required conditions for requested state
                    required_conditions = self._state_config.get(
                        requested_state, {}).get("conditions", [])

                    # Check if conditions are met
                    unmet_conditions = [
                        condition for condition in required_conditions
                        if not self._conditions.get(condition, False)
                    ]

                    if not unmet_conditions:
                        # Perform state transition
                        self._previous_state = self._current_state
                        self._current_state = requested_state

                        # Prepare state change message
                        change_data = {
                            "state": requested_state,
                            "previous": self._previous_state,
                            "description": self._state_config.get(requested_state, {}).get("description", ""),
                            "timestamp": datetime.now().isoformat()
                        }

                        if requested_state == "ERROR" and "error" in data:
                            change_data["error"] = data["error"]

                        # Publish state change
                        await self._message_broker.publish("state/change", change_data)

                        # Send success response
                        response_data.update({
                            "success": True,
                            "state": requested_state,
                            "previous": self._previous_state
                        })

                        logger.info(f"State changed from {self._previous_state} to {requested_state}")

                    else:
                        error_context = {
                            "requested_state": requested_state,
                            "current_state": self._current_state,
                            "unmet_conditions": unmet_conditions,
                            "conditions": self._conditions
                        }
                        raise StateError(f"Required conditions not met for {requested_state}", error_context)

                else:
                    error_context = {
                        "current_state": self._current_state,
                        "requested_state": requested_state,
                        "valid_transitions": valid_transitions
                    }
                    raise StateError(
                        f"Invalid state transition from {self._current_state} to {requested_state}",
                        error_context
                    )

            elif request_type == "get":
                # Return current state
                response_data.update({
                    "success": True,
                    "state": self._current_state,
                    "previous": self._previous_state,
                    "conditions": self._conditions,
                    "valid_transitions": self._state_config.get(self._current_state, {}).get("next_states", [])
                })

            else:
                raise StateError(f"Invalid request_type: {request_type}")

            # Send response
            await self._message_broker.publish("state/response", response_data)

        except Exception as e:
            error_context = {
                "source": "state_manager",
                "error": str(e),
                "request_id": data.get("request_id", ""),
                "request_type": request_type if 'request_type' in locals() else None,
                "requested_state": requested_state if 'requested_state' in locals() else None,
                "current_state": self._current_state,
                "timestamp": datetime.now().isoformat()
            }
            logger.error("Error handling state request", extra=error_context)
            await self._message_broker.publish("error", error_context)

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
                "hardware.plc.connected": ["hardware.plc.connected", "hardware.connected"],
                "hardware.motion.connected": ["hardware.motion.connected", "hardware.connected"],
                "hardware.plc.enabled": ["hardware.plc.enabled", "hardware.enabled"],
                "hardware.motion.enabled": ["hardware.motion.enabled", "hardware.enabled"],
                "sequence.active": ["sequence.active"],
                "hardware.safe": ["hardware.safe"]
            }

            if tag in condition_map:
                # Convert value to bool to ensure type safety
                bool_value = bool(value)

                # Update all mapped conditions
                for condition in condition_map[tag]:
                    self._conditions[condition] = bool_value

                    # Special handling for composite conditions
                    if condition == "hardware.connected":
                        self._conditions[condition] = all([
                            self._conditions["hardware.plc.connected"],
                            self._conditions["hardware.motion.connected"]
                        ])
                    elif condition == "hardware.enabled":
                        self._conditions[condition] = all([
                            self._conditions["hardware.plc.enabled"],
                            self._conditions["hardware.motion.enabled"]
                        ])

                logger.debug(f"Updated conditions for tag {tag}: {self._conditions}")

        except Exception as e:
            context = {
                "tag": tag if 'tag' in locals() else None,
                "value": value if 'value' in locals() else None,
                "error": str(e)
            }
            logger.error("Error handling tag update", extra=context)

    async def _handle_hardware_status(self, data: Dict[str, Any]) -> None:
        """Handle hardware status updates."""
        try:
            device = data.get("device")
            status = data.get("status")

            if not device or not status:
                context = {"received_data": data}
                logger.warning("Invalid hardware status update", extra=context)
                return

            # Map status to conditions
            if status == "connected":
                self._conditions[f"hardware.{device}.connected"] = True
                # Update composite condition
                self._conditions["hardware.connected"] = all([
                    self._conditions["hardware.plc.connected"],
                    self._conditions["hardware.motion.connected"]
                ])
            elif status == "disconnected":
                self._conditions[f"hardware.{device}.connected"] = False
                self._conditions["hardware.connected"] = False

            logger.debug(f"Updated hardware status for {device}: {status}")

        except Exception as e:
            context = {
                "data": data,
                "error": str(e)
            }
            logger.error("Error handling hardware status", extra=context)

    async def shutdown(self) -> None:
        """Shutdown state manager."""
        try:
            if not self._is_initialized:
                return

            # Unsubscribe from topics
            topics_and_handlers = [
                ("state/request", self._handle_state_request),
                ("tag/update", self._handle_tag_update),
                ("hardware/state", self._handle_hardware_status)
            ]

            for topic, handler in topics_and_handlers:
                await self._message_broker.unsubscribe(topic, handler)

            self._is_initialized = False
            logger.info("State manager shutdown complete")

        except Exception as e:
            context = {
                "current_state": self._current_state,
                "error": str(e)
            }
            logger.error("Error during state manager shutdown", extra=context)
            raise StateError("Failed to shutdown state manager", context) from e
