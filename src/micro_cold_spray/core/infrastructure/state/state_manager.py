"""State Manager component.

Manages system state according to state.yaml:
- State transitions
- State validation
- State error handling
- Message pattern compliance
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.exceptions import StateError


class StateManager:
    """Manages system state transitions."""

    def __init__(self, message_broker: MessageBroker, config_manager: ConfigManager):
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
        # Subscribe to state requests and hardware status
        await self._message_broker.subscribe("state/request", self._handle_state_request)
        await self._message_broker.subscribe("hardware/status/plc", self._handle_hardware_status)
        await self._message_broker.subscribe("hardware/status/motion", self._handle_motion_status)

    async def _handle_hardware_status(self, data: Dict[str, Any]) -> None:
        """Handle hardware status updates."""
        self._hardware_ready = data.get("connected", False)
        await self._check_ready()

    async def _handle_motion_status(self, data: Dict[str, Any]) -> None:
        """Handle motion status updates."""
        self._motion_ready = data.get("connected", False)
        await self._check_ready()

    async def _check_ready(self) -> None:
        """Check if system is ready for READY state."""
        if self._hardware_ready and self._motion_ready:
            if self._current_state == "INITIALIZING":
                await self.set_state("READY")

    async def set_state(self, new_state: str) -> None:
        """Set system state."""
        try:
            logger.debug(f"Attempting state transition: {self._current_state} -> {new_state}")
            
            # Validate transition
            if not self._is_valid_transition(new_state):
                error_msg = {
                    "error": f"Invalid state transition: {self._current_state} -> {new_state}",
                    "from": self._current_state,
                    "to": new_state,
                    "topic": "state/transition",
                    "timestamp": datetime.now().isoformat()
                }
                await self._message_broker.publish("error", error_msg)
                raise StateError(f"Invalid state transition from {self._current_state} to {new_state}")
            
            # Update state
            self._previous_state = self._current_state
            self._current_state = new_state
            
            # Publish state change
            await self._message_broker.publish(
                "state/change",
                {
                    "state": new_state,
                    "previous": self._previous_state,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error setting state: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "error": str(e),
                    "context": "state transition",
                    "topic": "state/transition",
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise

    async def _handle_state_request(self, data: Dict[str, Any]) -> None:
        """Handle state change requests."""
        try:
            requested_state = data.get("requested_state")
            if not requested_state:
                raise ValueError("No state requested")
            await self.set_state(requested_state)
            
        except Exception as e:
            logger.error(f"Error handling state request: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "error": str(e),
                    "context": "state request",
                    "topic": "state/request",
                    "timestamp": datetime.now().isoformat()
                }
            )

    def _is_valid_transition(self, new_state: str) -> bool:
        """Check if state transition is valid."""
        # Get valid transitions from config
        valid_transitions = self._config_manager.get_config("state").get(
            "transitions", {}).get(self._current_state, [])
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
            await self._message_broker.unsubscribe("hardware/status/plc", self._handle_hardware_status)
            await self._message_broker.unsubscribe("hardware/status/motion", self._handle_motion_status)
            logger.info("State manager shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise