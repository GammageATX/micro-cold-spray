from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from datetime import datetime

from ...infrastructure.state.state_manager import StateManager
from ...infrastructure.tags.tag_manager import TagManager
from ...infrastructure.messaging.message_broker import MessageBroker
from ...config.config_manager import ConfigManager
from ...exceptions import MonitorError

class StateMonitor:
    """Monitors overall system state using pub/sub."""
    
    def __init__(
        self,
        state_manager: StateManager,
        tag_manager: TagManager,
        message_broker: MessageBroker,
        config_manager: ConfigManager
    ):
        """Initialize monitor with required dependencies."""
        self._state_manager = state_manager
        self._tag_manager = tag_manager
        self._message_broker = message_broker
        
        # Get state definitions from config
        state_config = config_manager.get_config('state')
        self._state_transitions = state_config.get('transitions', {})
        
        self._current_states = {
            'system': 'INITIALIZING',
            'connection': 'DISCONNECTED',
            'motion': 'DISABLED',
            'process': 'INITIALIZING'
        }
        
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        logger.info("State monitor initialized")

    async def start(self) -> None:
        """Start state monitoring."""
        try:
            if self._is_running:
                logger.warning("State monitor already running")
                return

            self._is_running = True
            
            # Subscribe to state-related messages
            await self._message_broker.subscribe("state/change", self._handle_state_change)
            await self._message_broker.subscribe("state/error", self._handle_error_state)
            await self._message_broker.subscribe("hardware/event", self._handle_component_update)
            await self._message_broker.subscribe("process/update", self._handle_component_update)
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitor_states())
            logger.info("State monitoring started")

        except Exception as e:
            logger.exception("Failed to start state monitoring")
            raise MonitorError(f"State monitor start failed: {str(e)}") from e

    async def stop(self) -> None:
        """Stop state monitoring."""
        try:
            self._is_running = False
            
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
                
            logger.info("State monitoring stopped")

        except Exception as e:
            logger.exception("Error stopping state monitor")
            raise MonitorError(f"State monitor stop failed: {str(e)}") from e

    async def _handle_state_change(self, data: Dict[str, Any]) -> None:
        """Handle state change events."""
        try:
            # Forward state change
            await self._message_broker.publish(
                "state/change",
                {
                    "state": data["state"],
                    "type": data["type"],
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error handling state change: {e}")
            await self._message_broker.publish("state/change/error", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_error_state(self, data: Dict[str, Any]) -> None:
        """Handle error state updates."""
        try:
            error_message = data.get("message", "Unknown error")
            error_category = data.get("category", "system")
            
            # Update error state tags
            await self._tag_manager.set_tag(
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
            await self._tag_manager.set_tag(
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

    async def _monitor_states(self) -> None:
        """Monitor system states continuously."""
        try:
            while self._is_running:
                try:
                    # Check system state transitions
                    for state_type, transitions in self._state_transitions.items():
                        for current_state, allowed_transitions in transitions.items():
                            for target_state in allowed_transitions:
                                if self._current_states[state_type] == current_state:
                                    await self._handle_state_change({
                                        "type": state_type,
                                        "state": target_state
                                    })
                                    
                    await asyncio.sleep(1.0)  # State check interval
                    
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in state monitoring: {e}")
                    await asyncio.sleep(5.0)  # Error recovery delay
                    
        except asyncio.CancelledError:
            logger.info("State monitoring cancelled")
            raise
        except Exception as e:
            logger.exception("Fatal error in state monitoring")
            raise MonitorError(f"State monitoring failed: {str(e)}") from e