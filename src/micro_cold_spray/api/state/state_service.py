"""State management service."""

from typing import Dict, Any, Optional
from datetime import datetime
import os
import yaml
from loguru import logger
from fastapi import status

from micro_cold_spray.utils.errors import create_error


class StateService:
    """Service for managing system state."""
    
    def __init__(self):
        """Initialize state service."""
        self.version = "1.0.0"
        self.is_running = False
        self._current_state = "INITIALIZING"
        self._state_machine = {}
        self._history = []
        self._history_length = 1000  # Default history length
        self._start_time = None

    async def start(self):
        """Start state service."""
        try:
            if self.is_running:
                return
            
            # Load local state machine config
            config = await self._load_local_config()
            await self._apply_config(config)
            
            self.is_running = True
            self._start_time = datetime.now()
            logger.info(f"State service started with {len(self._state_machine)} states")
            
        except Exception as e:
            logger.error(f"Failed to start state service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start state service: {str(e)}"
            )

    async def stop(self):
        """Stop state service."""
        try:
            if not self.is_running:
                return
                
            self._add_history_entry("System shutdown")
            self.is_running = False
            logger.info("State service stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop state service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop state service: {str(e)}"
            )

    async def _load_local_config(self) -> Dict[str, Any]:
        """Load local state configuration.
        
        Returns:
            Dict[str, Any]: State configuration
            
        Raises:
            HTTPException: If configuration loading fails
        """
        try:
            # Get config path
            config_path = os.path.join(os.getcwd(), "config", "state.yaml")
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"State config file not found at {config_path}")
            
            # Read state config file
            with open(config_path, "r") as f:
                config_data = f.read()
            
            # Parse YAML content
            config = yaml.safe_load(config_data)
            
            # Validate config structure
            if not isinstance(config, dict):
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="Invalid state configuration: not a dict"
                )
            
            if "state" not in config:
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="Invalid state configuration: missing state section"
                )
                
            state_config = config["state"]
            if "initial_state" not in state_config or "transitions" not in state_config:
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="Invalid state configuration: missing required keys in state section"
                )
            
            return config
            
        except FileNotFoundError as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=str(e)
            )
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to load state configuration: {str(e)}"
            )

    async def _apply_config(self, config: Dict[str, Any]):
        """Apply configuration to state machine.
        
        Args:
            config: Configuration dict to apply
        """
        # Build state machine from transitions
        self._state_machine = {
            name: {
                "name": name,
                "valid_transitions": state_data["next_states"],
                "conditions": state_data.get("conditions", []),
                "description": state_data.get("description")
            }
            for name, state_data in config["state"]["transitions"].items()
        }
        
        # Set initial state if we're just starting
        if self._current_state == "INITIALIZING":
            self._current_state = config["state"].get("initial_state", "INITIALIZING")
            self._add_history_entry("System initialized")
    
    def _add_history_entry(self, message: str):
        """Add entry to state history.
        
        Args:
            message: History entry message
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "state": self._current_state,
            "message": message
        }
        
        self._history.append(entry)
        
        # Trim history if needed
        if len(self._history) > self._history_length:
            self._history = self._history[-self._history_length:]
    
    @property
    def current_state(self) -> str:
        """Get current state.
        
        Returns:
            str: Current state name
            
        Raises:
            HTTPException: If service not running (503)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="State service not running"
            )
        return self._current_state
    
    async def get_valid_transitions(self) -> Dict[str, Any]:
        """Get valid state transitions.
        
        Returns:
            Dict[str, Any]: Valid transitions for current state
            
        Raises:
            HTTPException: If service not running (503)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="State service not running"
            )
        
        current = self._state_machine.get(self._current_state)
        if not current:
            return {"valid_transitions": []}
            
        return {
            "current_state": self._current_state,
            "valid_transitions": current["valid_transitions"]
        }
    
    async def transition_to(self, new_state: str) -> Dict[str, Any]:
        """Transition to new state.
        
        Args:
            new_state: Target state name
            
        Returns:
            Dict[str, Any]: New state info
            
        Raises:
            HTTPException: If transition invalid (400) or service not running (503)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="State service not running"
            )
        
        current = self._state_machine.get(self._current_state)
        if not current:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid current state: {self._current_state}"
            )
        
        if new_state not in current["valid_transitions"]:
            raise create_error(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid transition from {self._current_state} to {new_state}"
            )
            
        # Update state and history
        old_state = self._current_state
        self._current_state = new_state
        self._add_history_entry(f"Transitioned from {old_state} to {new_state}")
        
        return {
            "old_state": old_state,
            "new_state": new_state,
            "valid_transitions": self._state_machine[new_state]["valid_transitions"]
        }
    
    async def get_history(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Get state transition history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            Dict[str, Any]: State history
            
        Raises:
            HTTPException: If service not running (503)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="State service not running"
            )
            
        history = self._history
        if limit:
            history = history[-limit:]
            
        return {
            "current_state": self._current_state,
            "history": history
        }
    
    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Dict[str, Any]: Health status
        """
        return {
            "status": "ok" if self.is_running else "error",
            "service": "state",
            "version": self.version,
            "is_running": self.is_running,
            "uptime": (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0,
            "error": None if self.is_running else "Service not running",
            "components": {
                "state_machine": {
                    "status": "ok" if self.is_running else "error",
                    "error": None if self.is_running else "State machine not running"
                }
            }
        }
