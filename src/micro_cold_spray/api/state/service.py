"""State management service."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from ..base import BaseService
from ..config import ConfigService
from ..messaging import MessagingService
from .models import (
    StateCondition,
    StateConfig,
    StateTransition,
    StateRequest,
    StateResponse
)
from .exceptions import StateTransitionError, InvalidStateError, ConditionError


logger = logging.getLogger(__name__)


class StateService(BaseService):
    """Service for managing system state transitions."""
    
    def __init__(
        self,
        config_service: ConfigService,
        message_broker: MessagingService
    ):
        """Initialize state service.
        
        Args:
            config_service: Configuration service
            message_broker: Message broker service
        """
        super().__init__(service_name="state", config_service=config_service)
        self._message_broker = message_broker
        self._current_state = "INIT"
        self._state_history: List[StateTransition] = []
        self._state_machine: Dict[str, StateConfig] = {}
        
    async def _start(self) -> None:
        """Initialize state service."""
        # Load state machine config
        config = await self._config_service.get_config("state_machine")
        self._state_machine = {
            name: StateConfig(
                name=name,
                valid_transitions=state_config["valid_transitions"],
                conditions={
                    cond_name: StateCondition(**cond_config)
                    for cond_name, cond_config in state_config.get("conditions", {}).items()
                },
                description=state_config.get("description")
            )
            for name, state_config in config["states"].items()
        }
        
        # Subscribe to state change requests
        await self._message_broker.subscribe(
            "state/request",
            self._handle_state_request
        )
        
        # Initialize state
        self._current_state = "INIT"
        self._add_history_entry("System initialized")
        
    async def transition_to(self, request: StateRequest) -> StateResponse:
        """Transition to a new state.
        
        Args:
            request: State transition request
            
        Returns:
            State transition response
            
        Raises:
            StateTransitionError: If transition is invalid or conditions not met
            InvalidStateError: If target state doesn't exist
        """
        target_state = request.target_state.upper()
        
        # Validate state exists
        if target_state not in self._state_machine:
            raise InvalidStateError(f"Unknown state: {target_state}")
        
        # Validate transition
        if not self._is_valid_transition(target_state):
            raise StateTransitionError(
                f"Invalid transition from {self._current_state} to {target_state}"
            )
            
        # Check conditions unless force flag is set
        if not request.force:
            conditions = await self.get_conditions(target_state)
            failed = [name for name, met in conditions.items() if not met]
            if failed:
                return StateResponse(
                    success=False,
                    old_state=self._current_state,
                    error=f"Conditions not met for {target_state}",
                    failed_conditions=failed,
                    timestamp=datetime.now()
                )
            
        # Perform transition
        try:
            old_state = self._current_state
            self._current_state = target_state
            timestamp = datetime.now()
            
            self._add_history_entry(
                StateTransition(
                    old_state=old_state,
                    new_state=target_state,
                    timestamp=timestamp,
                    reason=request.reason or "State change requested",
                    conditions_met=await self.get_conditions(target_state)
                )
            )
            
            # Notify subscribers
            await self._message_broker.publish(
                "state/changed",
                {
                    "old_state": old_state,
                    "new_state": target_state,
                    "timestamp": timestamp.isoformat(),
                    "reason": request.reason
                }
            )
            
            return StateResponse(
                success=True,
                old_state=old_state,
                new_state=target_state,
                timestamp=timestamp
            )
            
        except Exception as e:
            # Revert on failure
            self._current_state = old_state
            raise StateTransitionError(
                f"Transition failed: {str(e)}",
                {"error": str(e)}
            )
            
    def get_state_history(self, limit: Optional[int] = None) -> List[StateTransition]:
        """Get state transition history.
        
        Args:
            limit: Optional limit on number of entries to return
            
        Returns:
            List of state transition records
        """
        history = self._state_history.copy()
        if limit:
            history = history[-limit:]
        return history
        
    def get_valid_transitions(self) -> Dict[str, List[str]]:
        """Get map of valid state transitions.
        
        Returns:
            Dictionary mapping current states to lists of valid target states
        """
        return {
            state: config.valid_transitions
            for state, config in self._state_machine.items()
        }
        
    async def get_conditions(self, state: Optional[str] = None) -> Dict[str, bool]:
        """Get conditions for a state.
        
        Args:
            state: Optional state to check conditions for, defaults to current state
            
        Returns:
            Dictionary mapping condition names to their current status
            
        Raises:
            InvalidStateError: If state not found
        """
        state = state.upper() if state else self._current_state
        
        if state not in self._state_machine:
            raise InvalidStateError(f"Unknown state: {state}")
            
        conditions = self._state_machine[state].conditions
        return {
            name: await self._check_condition(condition)
            for name, condition in conditions.items()
        }
        
    def _is_valid_transition(self, target_state: str) -> bool:
        """Check if transition is valid.
        
        Args:
            target_state: State to check transition to
            
        Returns:
            True if transition is valid
        """
        if target_state not in self._state_machine:
            return False
            
        return target_state in self._state_machine[self._current_state].valid_transitions
        
    async def _check_condition(self, condition: StateCondition) -> bool:
        """Check if a condition is met.
        
        Args:
            condition: Condition configuration
            
        Returns:
            True if condition is met
            
        Raises:
            ConditionError: If condition check fails
        """
        try:
            # Get current value
            response = await self._message_broker.request(
                "tag/request",
                {"tag": condition.tag}
            )
            value = response["value"]
            
            # Check condition type
            if condition.type == "equals":
                return value == condition.value
            elif condition.type == "not_equals":
                return value != condition.value
            elif condition.type == "greater_than":
                return value > condition.value
            elif condition.type == "less_than":
                return value < condition.value
            elif condition.type == "in_range":
                return condition.min_value <= value <= condition.max_value
            else:
                logger.warning(f"Unknown condition type: {condition.type}")
                return False
                
        except Exception as e:
            raise ConditionError(f"Failed to check condition: {str(e)}")
            
    def _add_history_entry(self, entry: StateTransition) -> None:
        """Add entry to state history.
        
        Args:
            entry: State transition record
        """
        self._state_history.append(entry)
        
        # Limit history size
        if len(self._state_history) > 1000:
            self._state_history = self._state_history[-1000:]
            
    async def _handle_state_request(self, request: Dict[str, Any]) -> None:
        """Handle state change request.
        
        Args:
            request: State change request
        """
        try:
            state_request = StateRequest(
                target_state=request.get("state", ""),
                reason=request.get("reason"),
                force=request.get("force", False)
            )
            
            if not state_request.target_state:
                logger.warning("Missing target state in request")
                return
                
            await self.transition_to(state_request)
            
        except Exception as e:
            logger.error(f"Failed to handle state request: {str(e)}")
            
    @property
    def current_state(self) -> str:
        """Get current state name."""
        return self._current_state
