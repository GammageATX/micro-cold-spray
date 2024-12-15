"""State management service."""

from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger
import asyncio

from ..base import ConfigurableService
from ..config import ConfigService
from ..messaging import MessagingService
from ..communication.service import CommunicationService
from .models import (
    StateCondition,
    StateConfig,
    StateTransition,
    StateRequest,
    StateResponse
)
from .exceptions import (
    StateTransitionError,
    InvalidStateError,
    ConditionError,
    StateError
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
        super().__init__(service_name="state")
        self._config_service = config_service
        self._message_broker = message_broker
        self._communication_service = communication_service
        self._current_state = "INIT"
        self._state_history: List[StateTransition] = []
        self._state_machine: Dict[str, StateConfig] = {}
        
    @property
    def status(self) -> str:
        """Get service status."""
        if not self.is_running:
            return "stopped"
        if not self._state_machine:
            return "error"
        return "ok"

    @property
    def service_info(self) -> Dict[str, Any]:
        """Get service information."""
        return {
            "name": self.name,
            "version": "1.0.0",
            "running": self.is_running,
            "current_state": self._current_state,
            "states_configured": len(self._state_machine)
        }
        
    async def check_health(self) -> Dict[str, Any]:
        """Perform deep health check of the service and its dependencies.
        
        Returns:
            Dictionary containing health status and details
        """
        health_info = {
            "status": "ok",
            "dependencies": {},
            "details": {
                "current_state": self._current_state,
                "states_configured": len(self._state_machine),
                "history_entries": len(self._state_history)
            }
        }
        
        try:
            # Check config service
            config_health = {"status": "unknown"}
            try:
                await self._config_service.get_config("state")
                config_health = {"status": "ok"}
            except Exception as e:
                config_health = {"status": "error", "error": str(e)}
                health_info["status"] = "degraded"
            health_info["dependencies"]["config"] = config_health

            # Check message broker
            broker_health = {"status": "unknown"}
            try:
                await self._message_broker.request("health/check", {})
                broker_health = {"status": "ok"}
            except Exception as e:
                broker_health = {"status": "error", "error": str(e)}
                health_info["status"] = "degraded"
            health_info["dependencies"]["messaging"] = broker_health

            # Check communication service
            comm_health = {"status": "unknown"}
            try:
                if self._communication_service.is_running:
                    comm_health = {"status": "ok"}
                else:
                    comm_health = {"status": "error", "error": "Service not running"}
                    health_info["status"] = "degraded"
            except Exception as e:
                comm_health = {"status": "error", "error": str(e)}
                health_info["status"] = "degraded"
            health_info["dependencies"]["communication"] = comm_health

            # Check state machine configuration
            if not self._state_machine:
                health_info["status"] = "error"
                health_info["details"]["error"] = "No state machine configuration loaded"
            
            # If any dependency is down, mark as error
            if any(dep["status"] == "error" for dep in health_info["dependencies"].values()):
                health_info["status"] = "error"
                
        except Exception as e:
            health_info["status"] = "error"
            health_info["error"] = str(e)

        return health_info

    async def _start(self) -> None:
        """Initialize state service."""
        try:
            # Load state machine config
            config = await self._config_service.get_config("state")
            if not isinstance(config.data, dict):
                raise StateError("Invalid state configuration: not a dict")
            
            # Validate state config structure
            state_config = config.data
            if not isinstance(state_config, dict):
                raise StateError("Invalid state configuration structure")
                
            if "initial_state" not in state_config or "transitions" not in state_config:
                raise StateError("Invalid state configuration: missing required keys")
            
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
                        raise StateError(
                            "Failed to initialize messaging",
                            {"error": str(e)}
                        )
                    logger.warning(f"Retrying message subscription: {e}")
                    await asyncio.sleep(1)
            
            self._add_history_entry("System initialized")
            
            logger.info(
                f"State service started with {len(self._state_machine)} states"
            )
            
        except Exception as e:
            logger.error(f"Failed to start state service: {str(e)}")
            raise StateError("Failed to start state service", {"error": str(e)})
            
    async def _stop(self) -> None:
        """Cleanup service."""
        try:
            # Record shutdown
            self._add_history_entry("System shutdown")
            logger.info("State service stopped")
        except Exception as e:
            logger.error(f"Error stopping state service: {str(e)}")
            
    async def transition_to(self, request: StateRequest) -> StateResponse:
        """Handle state transition request."""
        if request.target_state not in self._state_machine:
            raise InvalidStateError(f"Invalid target state: {request.target_state}")
            
        # Check if transition is valid
        if request.target_state not in self._state_machine[self._current_state].valid_transitions:
            raise StateTransitionError(
                f"Invalid transition from {self._current_state} to {request.target_state}"
            )
            
        # Check conditions for target state
        conditions = await self.check_conditions(request.target_state)
        if not request.force and not all(conditions.values()):
            failed = [name for name, met in conditions.items() if not met]
            raise ConditionError(
                f"Conditions not met for {request.target_state}",
                {"failed_conditions": failed}
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
            ConditionError: If condition check fails
        """
        if not self.is_running:
            raise StateError("Service not running")
            
        state = state.upper() if state else self._current_state
        
        if state not in self._state_machine:
            logger.error(f"Unknown state: {state}")
            raise InvalidStateError(f"Unknown state: {state}")
            
        try:
            conditions = self._state_machine[state].conditions
            return {
                name: await self._check_condition(condition)
                for name, condition in conditions.items()
            }
        except Exception as e:
            logger.error(f"Failed to check conditions: {str(e)}")
            raise ConditionError(f"Failed to check conditions: {str(e)}")
        
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
            logger.error(f"Failed to check condition: {str(e)}")
            raise ConditionError(f"Failed to check condition: {str(e)}")
            
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
        """
        if state not in self._state_machine:
            raise InvalidStateError(f"Invalid state: {state}")
            
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
