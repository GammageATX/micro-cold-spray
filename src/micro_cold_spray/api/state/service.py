"""State management service for handling system states and transitions."""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Set
from datetime import datetime

from ..base import BaseService
from ...core.infrastructure.config.config_manager import ConfigManager
from ...core.infrastructure.messaging.message_broker import MessageBroker

logger = logging.getLogger(__name__)

class StateTransitionError(Exception):
    """Exception raised when a state transition is invalid."""
    pass

class StateService(BaseService):
    """Service for managing system state and transitions."""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        message_broker: MessageBroker
    ):
        super().__init__(service_name="state")
        self._config_manager = config_manager
        self._message_broker = message_broker
        
        # Internal state
        self._current_state = "INITIALIZING"
        self._previous_state = ""
        self._state_history: List[Dict[str, Any]] = []
        self._state_config: Dict[str, Any] = {}
        self._valid_states: Set[str] = set()
        self._is_initialized = False
        
        # Condition tracking
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
        
        # Configuration
        self._history_length = 1000  # Default history length
        self._transition_timeout = 5.0  # Default timeout in seconds
        self._transition_lock = asyncio.Lock()
        
    async def start(self) -> None:
        """Start the state service."""
        await super().start()
        
        try:
            if self._is_initialized:
                logger.warning("State service already initialized")
                return
                
            # Load configuration
            await self._load_config()
            
            # Set up event handlers
            await self._setup_event_handlers()
            
            self._is_initialized = True
            logger.info("State service started")
            
        except Exception as e:
            error_context = {
                "source": "state_service",
                "error": str(e),
                "context": {
                    "config": self._state_config,
                    "valid_states": list(self._valid_states)
                },
                "timestamp": datetime.now().isoformat()
            }
            logger.error("Failed to start state service", extra=error_context)
            await self._message_broker.publish("error", error_context)
            raise

    async def stop(self) -> None:
        """Stop the state service."""
        try:
            if not self._is_initialized:
                return
                
            # Unsubscribe from topics
            topics_and_handlers = [
                ("tag/update", self._handle_tag_update),
                ("hardware/state", self._handle_hardware_status)
            ]
            
            for topic, handler in topics_and_handlers:
                await self._message_broker.unsubscribe(topic, handler)
                
            self._is_initialized = False
            await super().stop()
            logger.info("State service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping state service: {e}")
            raise

    async def _load_config(self) -> None:
        """Load state configuration from state.yaml."""
        try:
            # Load state config
            config = await self._config_manager.get_config("state")
            self._state_config = config.get("state", {}).get("transitions", {})
            self._valid_states = set(self._state_config.keys())
            
            # Validate state configuration
            if not self._valid_states:
                raise StateTransitionError("No valid states defined in configuration")
                
            # Set initial state from config
            initial_state = config.get("state", {}).get("initial_state")
            if initial_state not in self._valid_states:
                raise StateTransitionError(
                    f"Invalid initial state: {initial_state}"
                )
                
            self._current_state = initial_state
            self._previous_state = ""
            
            # Load service settings
            service_config = await self._config_manager.get_config("application")
            settings = service_config.get("application", {}).get("services", {}).get("state_manager", {})
            
            self._history_length = settings.get("history_length", 1000)
            self._transition_timeout = settings.get("transition_timeout", 5000) / 1000.0
            
            logger.info("State configuration loaded")
            
        except Exception as e:
            logger.error(f"Failed to load state configuration: {e}")
            raise

    async def _setup_event_handlers(self) -> None:
        """Set up handlers for hardware and process events."""
        try:
            # Subscribe to hardware status updates
            await self._message_broker.subscribe(
                "hardware/state",
                self._handle_hardware_status
            )
            
            # Subscribe to tag updates
            await self._message_broker.subscribe(
                "tag/update",
                self._handle_tag_update
            )
            
            logger.info("Event handlers configured")
            
        except Exception as e:
            logger.error(f"Failed to set up event handlers: {e}")
            raise

    async def transition_to(self, target_state: str, request_id: Optional[str] = None) -> None:
        """
        Transition the system to a new state.
        
        Args:
            target_state: The state to transition to
            request_id: Optional request ID for tracking
            
        Raises:
            StateTransitionError: If transition is invalid
        """
        target_state = target_state.upper()
        
        # Acquire lock for state transition
        async with self._transition_lock:
            try:
                # Validate transition
                await self._validate_transition(target_state)
                
                # Record old state
                old_state = self._current_state
                
                # Notify transition start
                await self._notify_transition_start(target_state, request_id)
                
                # Update state
                self._previous_state = self._current_state
                self._current_state = target_state
                
                # Record in history
                self._record_transition(old_state, target_state)
                
                # Handle post-transition tasks
                await self._handle_post_transition(target_state, request_id)
                
                logger.info(f"Transitioned from {old_state} to {target_state}")
                
            except Exception as e:
                error_context = {
                    "source": "state_service",
                    "error": str(e),
                    "request_id": request_id,
                    "target_state": target_state,
                    "current_state": self._current_state,
                    "timestamp": datetime.now().isoformat()
                }
                logger.error("Failed to transition state", extra=error_context)
                await self._message_broker.publish("error", error_context)
                raise

    async def _validate_transition(self, target_state: str) -> None:
        """Validate if a transition is allowed."""
        if target_state not in self._valid_states:
            raise StateTransitionError(
                f"Invalid state: {target_state}"
            )
            
        # Get current state config
        current_config = self._state_config.get(self._current_state, {})
        
        # Check if target state is valid
        valid_next_states = current_config.get("next_states", [])
        if target_state not in valid_next_states:
            raise StateTransitionError(
                f"Invalid transition from {self._current_state} to {target_state}"
            )
            
        # Check conditions if they exist
        conditions = self._state_config.get(target_state, {}).get("conditions", [])
        if conditions:
            # Update conditions
            await self._update_conditions()
            
            # Check all conditions are met
            unmet_conditions = [
                condition for condition in conditions
                if not self._conditions.get(condition, False)
            ]
            
            if unmet_conditions:
                raise StateTransitionError(
                    f"Conditions not met for {target_state}: {unmet_conditions}"
                )

    async def _notify_transition_start(self, target_state: str, request_id: Optional[str] = None) -> None:
        """Notify system of upcoming state transition."""
        await self._message_broker.publish(
            "state/change",
            {
                "request_id": request_id,
                "from_state": self._current_state,
                "to_state": target_state,
                "timestamp": datetime.now().isoformat()
            }
        )

    def _record_transition(self, old_state: str, new_state: str) -> None:
        """Record a state transition in history."""
        self._state_history.append({
            "timestamp": datetime.now().isoformat(),
            "from_state": old_state,
            "to_state": new_state
        })
        
        # Trim history if needed
        if len(self._state_history) > self._history_length:
            self._state_history = self._state_history[-self._history_length:]

    async def _handle_post_transition(self, new_state: str, request_id: Optional[str] = None) -> None:
        """Handle any tasks needed after state transition."""
        response_data = {
            "request_id": request_id,
            "state": new_state,
            "previous": self._previous_state,
            "description": self._state_config.get(new_state, {}).get("description", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        await self._message_broker.publish("state/response", response_data)

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
                # Convert value to bool
                bool_value = bool(value)
                
                # Update all mapped conditions
                for condition in condition_map[tag]:
                    self._conditions[condition] = bool_value
                    
                    # Handle composite conditions
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
            logger.error(f"Error handling tag update: {e}")

    async def _handle_hardware_status(self, data: Dict[str, Any]) -> None:
        """Handle hardware status updates."""
        try:
            device = data.get("device")
            status = data.get("status")
            
            if not device or not status:
                logger.warning(f"Invalid hardware status update: {data}")
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
            logger.error(f"Error handling hardware status: {e}")

    async def _update_conditions(self) -> None:
        """Update all state conditions."""
        # Request latest hardware status
        await self._message_broker.publish(
            "hardware/request",
            {"command": "status"}
        )
        
        # Wait for responses (with timeout)
        await asyncio.sleep(self._transition_timeout)

    @property
    def current_state(self) -> str:
        """Get the current system state."""
        return self._current_state

    def get_state_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get the state transition history."""
        if limit is None:
            return self._state_history
        return self._state_history[-limit:]

    def get_valid_transitions(self) -> Dict[str, List[str]]:
        """Get map of valid state transitions."""
        return {
            state: config.get("next_states", [])
            for state, config in self._state_config.items()
        }

    async def get_conditions(self, state: Optional[str] = None) -> Dict[str, bool]:
        """Get conditions for a state."""
        await self._update_conditions()
        
        if state is None:
            state = self._current_state
            
        conditions = self._state_config.get(state, {}).get("conditions", [])
        return {
            condition: self._conditions.get(condition, False)
            for condition in conditions
        }
``` 