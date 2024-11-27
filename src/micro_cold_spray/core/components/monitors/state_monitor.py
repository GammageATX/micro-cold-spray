from typing import Dict, Any
import logging
import asyncio
from datetime import datetime

from ...infrastructure.state.state_manager import StateManager
from ...infrastructure.tags.tag_manager import TagManager
from ...infrastructure.messaging.message_broker import MessageBroker
from ...config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class StateMonitor:
    """Monitors overall system state using pub/sub."""
    
    def __init__(
        self,
        state_manager: StateManager,
        tag_manager: TagManager,
        config_manager: ConfigManager
    ):
        self._state_manager = state_manager
        self._tag_manager = tag_manager
        self._message_broker = MessageBroker()
        
        # Get state definitions from config
        state_config = config_manager.get_config('state')
        self._state_transitions = state_config['state']['transitions']
        
        # Initialize with correct starting states from config
        self._current_states = {
            'system': 'INITIALIZING',
            'connection': 'DISCONNECTED',
            'motion': 'DISABLED',
            'process': 'INITIALIZING'
        }
        
        self._running = False
        self._last_update = datetime.now()
        
        # Subscribe to state-related topics through MessageBroker
        self._message_broker.subscribe("state/change", self.on_message)
        self._message_broker.subscribe("state/error", self.on_message)
        self._message_broker.subscribe("hardware/event", self.on_message)
        self._message_broker.subscribe("process/update", self.on_message)
        
        logger.info("State monitor initialized")

    async def on_message(self, message: Dict[str, Any]) -> None:
        """Handle received messages."""
        try:
            if message['topic'] == "state/change":
                await self._handle_state_change(message['data'])
            elif message['topic'] == "state/error":
                await self._handle_error_state(message['data'])
            elif message['topic'].startswith(("hardware/", "process/", "safety/")):
                await self._handle_component_update(message['data'])
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            self._tag_manager.set_tag(
                "system.error",
                {
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _handle_state_change(self, data: Dict[str, Any]) -> None:
        """Handle system state changes."""
        try:
            state_type = data.get("type", "system")
            new_state = data.get("state")
            old_state = self._current_states.get(state_type)
            
            # Validate state transition
            if not self._validate_transition(state_type, old_state, new_state):
                logger.error(f"Invalid state transition: {old_state} -> {new_state}")
                return
                
            # Update state tracking
            self._current_states[state_type] = new_state
            self._last_update = datetime.now()
            
            # Update tags
            self._tag_manager.set_tag(
                f"{state_type}.state",
                {
                    "current": new_state,
                    "previous": old_state,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"{state_type} state transition: {old_state} -> {new_state}")
            
        except Exception as e:
            logger.error(f"Error handling state change: {e}")

    async def _handle_error_state(self, data: Dict[str, Any]) -> None:
        """Handle error state updates."""
        try:
            error_message = data.get("message", "Unknown error")
            error_category = data.get("category", "system")
            
            # Update error state tags
            self._tag_manager.set_tag(
                "system.error",
                {
                    "message": error_message,
                    "category": error_category,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.warning(f"System error ({error_category}): {error_message}")
            
        except Exception as e:
            logger.error(f"Error handling error state: {e}")

    async def _handle_component_update(self, data: Dict[str, Any]) -> None:
        """Handle component status updates."""
        try:
            component = data.get("component")
            status = data.get("status")
            
            if not status.get("healthy", True):
                logger.warning(f"Component issue detected: {component}")
                await self._handle_component_issue(component, status)
                
        except Exception as e:
            logger.error(f"Error handling component update: {e}")

    def _validate_transition(self, state_type: str, current: str, target: str) -> bool:
        """Validate state transition against config."""
        try:
            valid_transitions = self._state_transitions.get(state_type, {})
            allowed_transitions = valid_transitions.get(current, [])
            return target in allowed_transitions
            
        except Exception as e:
            logger.error(f"Error validating transition: {e}")
            return False

    async def _handle_component_issue(self, component: str, status: Dict[str, Any]) -> None:
        """Handle component issues."""
        try:
            # Update component status tag
            self._tag_manager.set_tag(
                f"{component}.status",
                {
                    "healthy": False,
                    "error": status.get("error", "Unknown issue"),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Check if we need to transition to error state
            if status.get("critical", False):
                await self._handle_state_change({
                    "type": "system",
                    "state": "ERROR",
                    "reason": f"Critical {component} issue"
                })
                
        except Exception as e:
            logger.error(f"Error handling component issue: {e}")

    async def start(self) -> None:
        """Start state monitoring."""
        logger.info("State monitoring started")
        self._running = True

    async def stop(self) -> None:
        """Stop state monitoring."""
        self._running = False
        logger.info("State monitoring stopped")