"""State service implementation."""

import os
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth


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
        self._service_name = "state"
        self._version = "1.0.0"  # Will be updated from config
        self._is_running = False
        self._start_time = None
        
        # Initialize components to None
        self._config = None
        self._current_state = None
        self._state_machine = {}
        self._history = []
        self._failed_transitions = {}  # Track failed transitions
        
        logger.info(f"{self.service_name} service initialized")
        
    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name
        
    @property
    def version(self) -> str:
        """Get service version."""
        return self._version
        
    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running
        
    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0
        
    @property
    def current_state(self) -> Optional[str]:
        """Get current state."""
        return self._current_state

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            # Load config and state machine
            await self._load_state_machine()
            
            logger.info(f"{self.service_name} service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def _load_state_machine(self) -> None:
        """Load state machine configuration."""
        try:
            # Load config
            self._config = load_config()
            self._version = self._config.get("version", self._version)
            
            # Load state machine
            self._state_machine = self._config.get("states", {})
            if not self._state_machine:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="No states defined in config"
                )
                
            # Set initial state
            initial_state = self._config.get("initial_state")
            if not initial_state:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="No initial state defined in config"
                )
            if initial_state not in self._state_machine:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid initial state: {initial_state}"
                )
                
            self._current_state = initial_state
            self._history = []
            
            # Clear any failed transitions for loaded states
            for state in self._state_machine:
                self._failed_transitions.pop(state, None)
                
        except Exception as e:
            logger.error(f"Failed to load state machine: {e}")
            self._failed_transitions["state_machine"] = str(e)

    async def _attempt_recovery(self) -> None:
        """Attempt to recover failed transitions."""
        if self._failed_transitions:
            logger.info(f"Attempting to recover {len(self._failed_transitions)} failed transitions...")
            await self._load_state_machine()

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )
            
            if not self._config:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"{self.service_name} service not initialized"
                )
            
            self._is_running = True
            self._start_time = datetime.now()
            
            # Add initial state to history
            self._history.append({
                "state": self._current_state,
                "timestamp": self._start_time.isoformat(),
                "transition": "initial"
            })
            
            logger.info(f"{self.service_name} service started")
            
        except Exception as e:
            self._is_running = False
            self._start_time = None
            error_msg = f"Failed to start {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service not running"
                )
            
            # 1. Clear state data
            self._current_state = None
            self._state_machine.clear()
            self._history.clear()
            
            # 2. Reset service state
            self._is_running = False
            self._start_time = None
            
            logger.info(f"{self.service_name} service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Attempt recovery of failed transitions
            await self._attempt_recovery()
            
            # Check component health
            config_ok = self._config is not None
            state_machine_ok = bool(self._state_machine)
            state_ok = self._current_state is not None
            
            # Build component statuses
            components = {
                "config": ComponentHealth(
                    status="ok" if config_ok else "error",
                    error=None if config_ok else "Configuration not loaded"
                ),
                "state_machine": ComponentHealth(
                    status="ok" if state_machine_ok else "error",
                    error=None if state_machine_ok else "State machine not initialized"
                ),
                "state": ComponentHealth(
                    status="ok" if state_ok else "error",
                    error=None if state_ok else "Current state not set"
                )
            }
            
            # Add failed transitions component if any exist
            if self._failed_transitions:
                failed_list = ", ".join(self._failed_transitions.keys())
                components["failed_transitions"] = ComponentHealth(
                    status="error",
                    error=f"Failed transitions: {failed_list}"
                )
            
            # Overall status is error only if state machine is completely invalid
            overall_status = "error" if not state_machine_ok else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more components in error state",
                components=components
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service=self.service_name,
                version=self.version,
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                components={name: ComponentHealth(status="error", error=error_msg)
                            for name in ["config", "state_machine", "state"]}
            )

    async def get_valid_transitions(self) -> List[str]:
        """Get valid state transitions from current state."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message=f"{self.service_name} service not running"
                )
            
            if not self._current_state:
                return []
                
            return self._state_machine.get(self._current_state, {}).get("transitions", [])
            
        except Exception as e:
            error_msg = f"Failed to get valid transitions: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def transition_to(self, new_state: str) -> Dict[str, Any]:
        """Transition to new state.
        
        Args:
            new_state: Target state name
            
        Returns:
            Dict[str, Any]: Updated state info
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message=f"{self.service_name} service not running"
                )
            
            # Validate new state
            if new_state not in self._state_machine:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid state: {new_state}"
                )
                
            # Check if transition is valid
            valid_transitions = await self.get_valid_transitions()
            if new_state not in valid_transitions:
                error_msg = f"Invalid transition from {self._current_state} to {new_state}"
                self._failed_transitions[f"{self._current_state}->{new_state}"] = error_msg
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=error_msg
                )
                
            # Update state
            old_state = self._current_state
            self._current_state = new_state
            
            # Add to history
            self._history.append({
                "state": new_state,
                "timestamp": datetime.now().isoformat(),
                "transition": f"{old_state} -> {new_state}"
            })
            
            # Clear failed transition if it exists
            self._failed_transitions.pop(f"{old_state}->{new_state}", None)
            
            logger.info(f"Transitioned from {old_state} to {new_state}")
            return {
                "previous_state": old_state,
                "current_state": new_state,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Failed to transition to {new_state}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get state transition history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List[Dict[str, Any]]: State transition history
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message=f"{self.service_name} service not running"
                )
            
            history = self._history
            if limit:
                history = history[-limit:]
            return history
            
        except Exception as e:
            error_msg = f"Failed to get history: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )
