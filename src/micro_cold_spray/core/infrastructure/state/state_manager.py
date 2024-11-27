"""System state management."""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ..messaging.message_broker import MessageBroker
from ...config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class StateManager:
    """Manages system state transitions."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, message_broker: MessageBroker, config_manager: ConfigManager):
        if self._initialized:
            return
        
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._logger = logging.getLogger(__name__)
        
        # Load state configuration
        self._state_config = self._config_manager.get_config('state')
        
        # Subscribe to state change requests and config updates
        self._message_broker.subscribe("state/request", self._handle_state_request)
        self._message_broker.subscribe("config/update/state", self._handle_config_update)
        
        # Initialize state asynchronously in start() method
        self._initialized = True
        logger.info("State manager initialized")

    async def start(self) -> None:
        """Initialize state tags."""
        try:
            # Initialize state tags through MessageBroker
            await self._message_broker.publish("tag/set", {
                "tag": "system_state.state",
                "value": "INITIALIZING",
                "timestamp": datetime.now().isoformat()
            })
            
            await self._message_broker.publish("tag/set", {
                "tag": "system_state.previous_state",
                "value": "",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error initializing state: {e}")

    async def _handle_config_update(self, data: Dict[str, Any]) -> None:
        """Handle configuration updates."""
        try:
            self._state_config.update(data)
            logger.info("State configuration updated")
        except Exception as e:
            logger.error(f"Error handling config update: {e}")

    async def _handle_state_request(self, request_data: Dict[str, Any]) -> None:
        """Handle state change requests."""
        try:
            requested_state = request_data.get("requested_state")
            # Implement state change logic here
            logger.info(f"State change requested: {requested_state}")
        except Exception as e:
            logger.error(f"Error handling state request: {e}")

    async def get_current_state(self) -> str:
        """Get the current system state."""
        try:
            response = await self._message_broker.request(
                "tag/get",
                {
                    "tag": "system_state.state"
                }
            )
            if response is None:
                self._logger.error("No response received for current state request")
                return 'UNKNOWN'
            
            return response.get('value', 'UNKNOWN')
        
        except Exception as e:
            self._logger.error(f"Error getting current state: {e}")
            return 'ERROR'

    async def get_previous_state(self) -> Optional[str]:
        """Get the previous system state."""
        try:
            response = await self._message_broker.request(
                "tag/get",
                {
                    "tag": "system_state.previous_state"
                }
            )
            if response is None:
                self._logger.error("No response received for previous state request")
                return None
            
            return response.get('value')
        
        except Exception as e:
            self._logger.error(f"Error getting previous state: {e}")
            return None

    async def set_state(self, new_state: str) -> None:
        """Set the system state."""
        try:
            current_state = await self.get_current_state()
            
            # Don't update if state hasn't changed
            if current_state == new_state:
                return
                
            # Check if transition is allowed
            if not await self.can_transition_to(new_state):
                self._logger.error(f"Invalid state transition from {current_state} to {new_state}")
                return
                
            # Update state tags through MessageBroker
            timestamp = datetime.now().isoformat()
            
            await self._message_broker.publish("tag/set", {
                "tag": "system_state.previous_state",
                "value": current_state,
                "timestamp": timestamp
            })
            
            await self._message_broker.publish("tag/set", {
                "tag": "system_state.state",
                "value": new_state,
                "timestamp": timestamp
            })
            
            await self._message_broker.publish("tag/set", {
                "tag": "system_state.state_changed",
                "value": timestamp,
                "timestamp": timestamp
            })
            
            # Publish state change event
            await self._message_broker.publish("state/change", {
                "previous_state": current_state,
                "current_state": new_state,
                "timestamp": timestamp
            })
            
            self._logger.info(f"State changed from {current_state} to {new_state}")
            
        except Exception as e:
            self._logger.error(f"Error setting state: {e}")
            raise

    async def can_transition_to(self, target_state: str) -> bool:
        """Check if transition to target state is allowed."""
        try:
            current_state = await self.get_current_state()
            
            # Get valid transitions from config
            transitions = self._state_config.get('state', {}).get('transitions', {}).get('system', {})
            valid_transitions = transitions.get(current_state, [])
            
            return target_state in valid_transitions
            
        except Exception as e:
            self._logger.error(f"Error checking state transition: {e}")
            return False