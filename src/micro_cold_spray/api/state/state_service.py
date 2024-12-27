"""State service implementation."""

import os
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, get_uptime


def load_config() -> Dict[str, Any]:
    """Load state service configuration.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    config_path = os.path.join("config", "state.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


class StateService:
    """State service implementation."""
    
    def __init__(self):
        """Initialize state service."""
        self._config = None
        self._version = "1.0.0"
        self._is_running = False
        self._start_time = None
        self._current_state = None
        self._state_machine = {}
        self._history = []
        
    @property
    def version(self) -> str:
        """Get service version.
        
        Returns:
            str: Service version
        """
        return self._version
        
    @property
    def is_running(self) -> bool:
        """Get service running state.
        
        Returns:
            bool: True if service is running
        """
        return self._is_running
        
    @property
    def uptime(self) -> float:
        """Get service uptime in seconds.
        
        Returns:
            float: Uptime in seconds
        """
        if not self._start_time:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()
        
    @property
    def current_state(self) -> Optional[str]:
        """Get current state.
        
        Returns:
            Optional[str]: Current state name
        """
        return self._current_state
        
    async def initialize(self):
        """Initialize service."""
        try:
            logger.info("Initializing state service...")
            
            # Load config
            self._config = load_config()
            self._version = self._config.get("version", self._version)
            
            # Load state machine
            self._state_machine = self._config.get("states", {})
            if not self._state_machine:
                raise ValueError("No states defined in config")
                
            # Set initial state
            initial_state = self._config.get("initial_state")
            if not initial_state:
                raise ValueError("No initial state defined in config")
            if initial_state not in self._state_machine:
                raise ValueError(f"Invalid initial state: {initial_state}")
                
            self._current_state = initial_state
            self._history = []
            
            logger.info("State service initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize state service: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
            
    async def start(self):
        """Start service."""
        if self.is_running:
            logger.warning("State service already running")
            return
            
        try:
            logger.info("Starting state service...")
            
            # Initialize if not already initialized
            if not self._config:
                await self.initialize()
                
            self._is_running = True
            self._start_time = datetime.now()
            
            # Add initial state to history
            self._history.append({
                "state": self._current_state,
                "timestamp": self._start_time.isoformat(),
                "transition": "initial"
            })
            
            logger.info("State service started successfully")
            
        except Exception as e:
            error_msg = f"Failed to start state service: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
            
    async def stop(self):
        """Stop service."""
        if not self.is_running:
            logger.warning("State service already stopped")
            return
            
        try:
            logger.info("Stopping state service...")
            
            self._is_running = False
            self._start_time = None
            
            logger.info("State service stopped successfully")
            
        except Exception as e:
            error_msg = f"Failed to stop state service: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
            
    async def health(self) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Health status
        """
        try:
            is_healthy = self.is_running and self._config is not None
            
            return ServiceHealth(
                status="ok" if is_healthy else "error",
                service="state",
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if is_healthy else "Service not healthy",
                components={
                    "state_machine": {
                        "status": "ok" if is_healthy else "error",
                        "error": None if is_healthy else "State machine not healthy"
                    }
                }
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="state",
                version=self.version,
                is_running=False,
                uptime=0.0,
                error=error_msg,
                components={
                    "state_machine": {
                        "status": "error",
                        "error": error_msg
                    }
                }
            )
            
    async def get_valid_transitions(self) -> List[str]:
        """Get valid state transitions from current state.
        
        Returns:
            List[str]: List of valid transition states
        """
        if not self.is_running:
            raise RuntimeError("Service not running")
            
        if not self._current_state:
            return []
            
        current_state_def = self._state_machine.get(self._current_state, {})
        return list(current_state_def.get("transitions", {}).keys())
        
    async def transition_to(self, new_state: str) -> Dict[str, Any]:
        """Transition to new state.
        
        Args:
            new_state (str): New state name
            
        Returns:
            Dict[str, Any]: Transition result
        """
        if not self.is_running:
            raise RuntimeError("Service not running")
            
        if not self._current_state:
            raise RuntimeError("No current state")
            
        if new_state not in self._state_machine:
            raise ValueError(f"Invalid state: {new_state}")
            
        current_state_def = self._state_machine.get(self._current_state, {})
        transitions = current_state_def.get("transitions", {})
        
        if new_state not in transitions:
            raise ValueError(f"Invalid transition from {self._current_state} to {new_state}")
            
        # Record transition
        timestamp = datetime.now()
        self._history.append({
            "state": new_state,
            "timestamp": timestamp.isoformat(),
            "transition": f"{self._current_state} -> {new_state}"
        })
        
        # Update state
        self._current_state = new_state
        
        return {
            "previous_state": self._current_state,
            "new_state": new_state,
            "timestamp": timestamp.isoformat()
        }
        
    async def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get state transition history.
        
        Args:
            limit (Optional[int]): Maximum number of history entries to return
            
        Returns:
            List[Dict[str, Any]]: State transition history
        """
        if not self.is_running:
            raise RuntimeError("Service not running")
            
        if limit is not None and limit > 0:
            return self._history[-limit:]
            
        return self._history
