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
        try:
            # Subscribe to state requests and tag updates
            await self._message_broker.subscribe("state/request", self._handle_state_request)
            await self._message_broker.subscribe("tag/update", self._handle_tag_update)
            
            # Load state config
            config = self._config_manager.get_config("state")
            logger.debug(f"Loaded state config: {config}")
            
            # Get transitions from state config
            self._state_config = config.get("state", {}).get("transitions", {})  # Fixed path to transitions
            
            # Start in INITIALIZING state
            self._current_state = "INITIALIZING"
            self._previous_state = ""
            
            # Initialize condition tracking
            self._conditions = {
                "hardware.connected": False,
                "config.loaded": True,  # Set by ConfigManager
                "hardware.enabled": False,
                "sequence.active": False
            }
            
            # Subscribe to hardware status
            await self._message_broker.subscribe("hardware/status/plc", self._handle_hardware_status)
            await self._message_broker.subscribe("hardware/status/motion", self._handle_hardware_status)
            
            logger.info("State manager initialization complete")
            
        except Exception as e:
            logger.exception("Failed to initialize state manager")
            raise StateError(f"State manager initialization failed: {str(e)}") from e

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle tag updates and check conditions."""
        try:
            tag = data.get("tag")
            value = data.get("value")
            logger.debug(f"Handling tag update: {tag} = {value}")
            
            # Update condition based on tag
            if tag == "hardware.connected":
                self._conditions["hardware.connected"] = value
                logger.debug(f"Updated hardware.connected to {value}")
                await self._check_conditions()
                
            elif tag == "hardware.enabled":
                self._conditions["hardware.enabled"] = value
                logger.debug(f"Updated hardware.enabled to {value}")
                await self._check_conditions()
                
            elif tag == "sequence.active":
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
                if self._conditions.get("hardware.connected") and self._conditions.get("config.loaded"):
                    logger.debug("Conditions met for READY transition")
                    
                    # Request state change
                    await self._message_broker.publish("state/request", {
                        "state": "READY",
                        "timestamp": datetime.now().isoformat()
                    })
                    
        except Exception as e:
            logger.error(f"Error checking conditions: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "topic": "state/conditions",
                "context": "condition_check",
                "timestamp": datetime.now().isoformat()
            })

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
            current_state_config = self._state_config.get(self._current_state, {})
            valid_transitions = current_state_config.get("next_states", [])
            required_conditions = current_state_config.get("conditions", [])
            
            # Check if transition is valid and conditions are met
            if requested_state in valid_transitions:
                # Check conditions
                conditions_met = all(self._conditions.get(cond, False) for cond in required_conditions)
                
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
                    logger.info(f"State changed from {self._previous_state} to {self._current_state}")
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
                error_msg = f"Invalid state transition from {self._current_state} to {requested_state}"
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
            await self._message_broker.unsubscribe("tag/update", self._handle_tag_update)
            logger.info("State manager shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise

    async def _handle_hardware_status(self, data: Dict[str, Any]) -> None:
        """Handle hardware status updates."""
        try:
            logger.debug(f"Handling hardware status: {data}")
            if isinstance(data, dict) and data.get("connected"):
                # Convert hardware status to tag update
                await self._handle_tag_update({
                    "tag": "hardware.connected",
                    "value": True,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error handling hardware status: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "topic": "hardware/status",
                "context": "hardware_status",
                "timestamp": datetime.now().isoformat()
            })