"""State management service."""

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from loguru import logger
import asyncio
from fastapi import status

from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.communication.communication_service import CommunicationService
from .state_models import (
    StateCondition,
    StateConfig,
    StateTransition,
    StateRequest,
    StateResponse
)


class StateService(ConfigurableService):
    """Service for managing system state transitions."""
    
    # Maximum history entries to keep
    MAX_HISTORY_SIZE = 1000
    
    def __init__(
        self,
        config_service: ConfigService,
        message_broker: MessagingService,
        communication_service: CommunicationService
    ):
        """Initialize state service."""
        super().__init__(service_name="state", config_service=config_service)
        self._message_broker = message_broker
        self._communication_service = communication_service
        self._current_state = "INIT"
        self._state_history: List[StateTransition] = []
        self._state_machine: Dict[str, StateConfig] = {}
        self._state_conditions: Dict[str, Dict[str, Callable[[], bool]]] = {}
        self._state_handlers: Dict[str, Callable[[], None]] = {}
        
    async def initialize(self) -> None:
        """Initialize service.
        
        Raises:
            HTTPException: If initialization fails (503)
        """
        try:
            await super().initialize()
            
            # Load state machine config
            config = await self._config_service.get_config("state")
            if not isinstance(config.data, dict):
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="Invalid state configuration: not a dict"
                )
            
            # Validate state config structure
            state_config = config.data
            if not isinstance(state_config, dict):
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="Invalid state configuration structure"
                )
                
            if "initial_state" not in state_config or "transitions" not in state_config:
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="Invalid state configuration: missing required keys"
                )
            
            # Build state machine from transitions
            self._state_machine = {
                name: StateConfig(
                    name=name,
                    valid_transitions=state_data["next_states"],
                    conditions={
                        cond_name: StateCondition(
                            tag=cond_name,
                            type="equals",  # Default to equals comparison
                            value=True      # Default to checking for True
                        )
                        for cond_name in state_data.get("conditions", [])
                    },
                    description=state_data.get("description")
                )
                for name, state_data in state_config["transitions"].items()
            }
            
            # Set initial state
            self._current_state = state_config.get("initial_state", "INITIALIZING")
            
            # Wait for message broker to be ready
            retries = 3
            while retries > 0:
                try:
                    # Subscribe to state change requests
                    await self._message_broker.subscribe(
                        "state/request",
                        self._handle_state_request
                    )
                    break
                except Exception as e:
                    retries -= 1
                    if retries == 0:
                        raise create_error(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            message="Failed to initialize messaging",
                            context={"error": str(e)},
                            cause=e
                        )
                    logger.warning(f"Retrying message subscription: {e}")
                    await asyncio.sleep(1)
            
            self._add_history_entry("System initialized")
            
            logger.info(
                f"State service started with {len(self._state_machine)} states"
            )
            
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to initialize state service",
                context={"error": str(e)},
                cause=e
            )
            
    async def start(self) -> None:
        """Start service.
        
        Raises:
            HTTPException: If start fails (503)
        """
        try:
            await super().start()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to start state service",
                context={"error": str(e)},
                cause=e
            )
            
    async def stop(self) -> None:
        """Stop service.
        
        Raises:
            HTTPException: If stop fails (503)
        """
        try:
            # Record shutdown
            self._add_history_entry("System shutdown")
            await super().stop()
            logger.info("State service stopped")
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to stop state service",
                context={"error": str(e)},
                cause=e
            )
            
    async def transition_to(self, request: StateRequest) -> StateResponse:
        """Handle state transition request.
        
        Args:
            request: State change request
            
        Returns:
            State change response
            
        Raises:
            HTTPException: If transition fails (400, 404, 409, 503)
        """
        if request.target_state not in self._state_machine:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Invalid target state: {request.target_state}"
            )
            
        # Check if transition is valid
        if request.target_state not in self._state_machine[self._current_state].valid_transitions:
            raise create_error(
                status_code=status.HTTP_409_CONFLICT,
                message=f"Invalid transition from {self._current_state} to {request.target_state}"
            )
            
        try:
            # Check conditions for target state
            conditions = await self.check_conditions(request.target_state)
            if not request.force and not all(conditions.values()):
                failed = [name for name, met in conditions.items() if not met]
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Conditions not met for {request.target_state}",
                    context={"failed_conditions": failed}
                )
                
            # Perform transition
            old_state = self._current_state
            self._current_state = request.target_state
            
            # Record transition
            self._add_history_entry(
                StateTransition(
                    old_state=old_state,
                    new_state=request.target_state,
                    timestamp=datetime.now(),
                    reason=request.reason or "Manual transition",
                    conditions_met=conditions
                )
            )
            
            # Notify via messaging
            await self._message_broker.publish(
                "state/changed",
                {
                    "success": True,
                    "old_state": old_state,
                    "new_state": self._current_state,
                    "timestamp": datetime.now().isoformat(),
                    "conditions": conditions
                }
            )
            
            return StateResponse(
                success=True,
                old_state=old_state,
                new_state=self._current_state,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to transition state",
                context={"error": str(e)},
                cause=e
            )
        
    def get_state_history(self, limit: Optional[int] = None) -> List[StateTransition]:
        """Get state transition history.
        
        Args:
            limit: Optional limit on number of entries to return
            
        Returns:
            List of state transition records
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            history = self._state_history.copy()
            if limit:
                history = history[-limit:]
            return history
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get state history",
                context={"error": str(e)},
                cause=e
            )
        
    def get_valid_transitions(self) -> Dict[str, List[str]]:
        """Get map of valid state transitions.
        
        Returns:
            Dictionary mapping current states to lists of valid target states
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return {
                state: config.valid_transitions
                for state, config in self._state_machine.items()
            }
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get valid transitions",
                context={"error": str(e)},
                cause=e
            )
        
    async def get_conditions(self, state: Optional[str] = None) -> Dict[str, bool]:
        """Get conditions for a state.
        
        Args:
            state: Optional state to check conditions for, defaults to current state
            
        Returns:
            Dictionary mapping condition names to their current status
            
        Raises:
            HTTPException: If state not found (404) or service unavailable (503)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running"
            )
            
        state = state.upper() if state else self._current_state
        
        if state not in self._state_machine:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Unknown state: {state}"
            )
            
        try:
            conditions = self._state_machine[state].conditions
            return {
                name: await self._check_condition(condition)
                for name, condition in conditions.items()
            }
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to check conditions",
                context={"error": str(e)},
                cause=e
            )
        
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
            HTTPException: If condition check fails (503)
        """
        try:
            # Get current value
            try:
                response = await self._message_broker.request(
                    "tag/request",
                    {"tag": condition.tag}
                )
                value = response["value"]
            except Exception as e:
                logger.warning(f"Failed to get tag value for {condition.tag}: {e}")
                return False
            
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
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to check condition",
                context={"error": str(e)},
                cause=e
            )
            
    def _add_history_entry(self, entry: StateTransition | str) -> None:
        """Add entry to state history.
        
        Args:
            entry: State transition record or message
        """
        if isinstance(entry, str):
            entry = StateTransition(
                old_state=self._current_state,
                new_state=self._current_state,
                timestamp=datetime.now(),
                reason=entry,
                conditions_met={}
            )
            
        self._state_history.append(entry)
        
        # Limit history size
        if len(self._state_history) > self.MAX_HISTORY_SIZE:
            self._state_history = self._state_history[-self.MAX_HISTORY_SIZE:]
            
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

    async def check_conditions(self, state: str) -> Dict[str, bool]:
        """Check if conditions are met for a state.
        
        Args:
            state: State to check conditions for
            
        Returns:
            Dict mapping condition names to their current status
            
        Raises:
            HTTPException: If state not found (404) or service unavailable (503)
        """
        if state not in self._state_machine:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Invalid state: {state}"
            )
            
        try:
            conditions = {}
            for condition_name, _ in self._state_machine[state].conditions.items():
                try:
                    if condition_name == "hardware.connected":
                        response = await self._message_broker.request(
                            "hardware/state",
                            {"query": "connection"}
                        )
                        conditions[condition_name] = response.get("connected", False)
                        
                    elif condition_name == "hardware.enabled":
                        response = await self._message_broker.request(
                            "hardware/state",
                            {"query": "enabled"}
                        )
                        conditions[condition_name] = response.get("enabled", False)
                        
                    elif condition_name == "hardware.safe":
                        response = await self._message_broker.request(
                            "hardware/state",
                            {"query": "safety"}
                        )
                        conditions[condition_name] = response.get("safe", False)
                        
                    elif condition_name == "config.loaded":
                        response = await self._message_broker.request(
                            "config/request",
                            {"query": "status"}
                        )
                        conditions[condition_name] = response.get("loaded", False)
                        
                    elif condition_name == "sequence.active":
                        response = await self._message_broker.request(
                            "sequence/state",
                            {}
                        )
                        conditions[condition_name] = response.get("active", False)
                    
                    else:
                        logger.warning(f"Unknown condition: {condition_name}")
                        conditions[condition_name] = False
                        
                except Exception as e:
                    logger.error(f"Failed to check condition {condition_name}: {e}")
                    conditions[condition_name] = False
                
            return conditions
            
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to check conditions",
                context={"error": str(e)},
                cause=e
            )

    @property
    def name(self) -> str:
        """Get service name."""
        return "state"
