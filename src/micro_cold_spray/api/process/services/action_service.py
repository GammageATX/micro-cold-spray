"""Action management service."""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from ...base import BaseService
from ...config import ConfigService
from ...communication import CommunicationService, HardwareError
from ...messaging import MessagingService
from ..exceptions import ProcessError


class ActionService(BaseService):
    """Service for managing process actions and commands."""

    def __init__(
        self,
        config_service: ConfigService,
        comm_service: CommunicationService,
        message_broker: MessagingService
    ):
        """Initialize action service.
        
        Args:
            config_service: Configuration service
            comm_service: Communication service for hardware control
            message_broker: Message broker service
        """
        super().__init__(service_name="action", config_service=config_service)
        self._comm_service = comm_service
        self._message_broker = message_broker
        self._config: Dict[str, Any] = {}
        self._current_action: Optional[Dict[str, Any]] = None
        self._hardware_state: Dict[str, Any] = {}

    async def _start(self) -> None:
        """Initialize action service."""
        try:
            # Load configuration
            config = await self._config_service.get_config("process")
            self._config = config.get("process", {})
            
            # Initialize hardware state tracking
            self._hardware_state = {
                "spray_active": False,
                "motion_active": False,
                "last_position": None,
                "last_spray_state": None
            }
            
            logger.info("Action service started")
            
        except Exception as e:
            error_context = {"source": "action_service", "error": str(e)}
            logger.error("Failed to start action service", extra=error_context)
            raise ProcessError("Failed to start action service", error_context)

    async def _stop(self) -> None:
        """Stop action service."""
        try:
            # Cleanup any active actions
            if self._current_action:
                await self.abort_current_action()
                
            # Reset hardware state
            await self._reset_hardware_state()
            
            logger.info("Action service stopped")
            
        except Exception as e:
            error_context = {"source": "action_service", "error": str(e)}
            logger.error("Failed to stop action service", extra=error_context)
            raise ProcessError("Failed to stop action service", error_context)

    async def execute_action(self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Execute process action.
        
        Args:
            action_type: Type of action to execute
            parameters: Action parameters
            
        Raises:
            ProcessError: If action execution fails
        """
        if not self.is_running:
            raise ProcessError("Service not running")

        try:
            if self._current_action:
                raise ProcessError("Another action is already in progress")

            # Validate action type
            if action_type not in self._config.get("actions", {}).get("types", []):
                raise ProcessError(f"Invalid action type: {action_type}")

            # Validate parameters
            await self._validate_action_parameters(action_type, parameters)

            self._current_action = {
                "type": action_type,
                "parameters": parameters,
                "status": "running",
                "start_time": datetime.now().isoformat()
            }

            # Execute action based on type
            if action_type == "move":
                await self._execute_move(parameters)
            elif action_type == "spray":
                await self._execute_spray(parameters)
            elif action_type == "pause":
                await self._execute_pause(parameters)
            else:
                await self._execute_custom_action(action_type, parameters)

            self._current_action["status"] = "completed"
            self._current_action["end_time"] = datetime.now().isoformat()
            
        except HardwareError as e:
            if self._current_action:
                self._current_action["status"] = "failed"
                self._current_action["error"] = str(e)
                self._current_action["end_time"] = datetime.now().isoformat()
            error_context = {
                "type": action_type,
                "parameters": parameters,
                "error": str(e),
                "device": e.device
            }
            logger.error("Hardware error during action", extra=error_context)
            raise ProcessError("Hardware error during action", error_context)
        except Exception as e:
            if self._current_action:
                self._current_action["status"] = "failed"
                self._current_action["error"] = str(e)
                self._current_action["end_time"] = datetime.now().isoformat()
            error_context = {
                "type": action_type,
                "parameters": parameters,
                "error": str(e)
            }
            logger.error("Failed to execute action", extra=error_context)
            raise ProcessError("Failed to execute action", error_context)
        finally:
            self._current_action = None

    async def get_current_action(self) -> Optional[Dict[str, Any]]:
        """Get currently executing action.
        
        Returns:
            Current action data or None if no action is running
        """
        if not self.is_running:
            raise ProcessError("Service not running")
            
        return self._current_action

    async def abort_current_action(self) -> None:
        """Abort currently executing action.
        
        Raises:
            ProcessError: If no action is running or abort fails
        """
        if not self.is_running:
            raise ProcessError("Service not running")

        if not self._current_action:
            raise ProcessError("No action is currently running")

        try:
            # Stop hardware operations
            await self._reset_hardware_state()
            
            self._current_action["status"] = "aborted"
            self._current_action["end_time"] = datetime.now().isoformat()
            self._current_action = None
            
        except Exception as e:
            error_context = {
                "action": self._current_action,
                "error": str(e)
            }
            logger.error("Failed to abort action", extra=error_context)
            raise ProcessError("Failed to abort action", error_context)

    async def _validate_action_parameters(self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Validate action parameters.
        
        Args:
            action_type: Type of action
            parameters: Action parameters
            
        Raises:
            ProcessError: If parameters are invalid
        """
        try:
            action_schema = self._config.get("actions", {}).get("schemas", {}).get(action_type)
            if not action_schema:
                raise ProcessError(f"No schema defined for action type: {action_type}")

            # Validate required parameters
            required = action_schema.get("required", [])
            for param in required:
                if param not in parameters:
                    raise ProcessError(f"Missing required parameter: {param}")

            # Validate parameter types and ranges
            param_types = action_schema.get("parameters", {})
            for param, value in parameters.items():
                if param not in param_types:
                    raise ProcessError(f"Unknown parameter: {param}")

                param_type = param_types[param].get("type")
                if param_type == "number":
                    if not isinstance(value, (int, float)):
                        raise ProcessError(f"Invalid type for {param}: expected number")
                    min_val = param_types[param].get("min")
                    max_val = param_types[param].get("max")
                    if min_val is not None and value < min_val:
                        raise ProcessError(f"Parameter {param} below minimum: {min_val}")
                    if max_val is not None and value > max_val:
                        raise ProcessError(f"Parameter {param} above maximum: {max_val}")
                elif param_type == "string":
                    if not isinstance(value, str):
                        raise ProcessError(f"Invalid type for {param}: expected string")
                    allowed = param_types[param].get("enum")
                    if allowed and value not in allowed:
                        raise ProcessError(f"Invalid value for {param}: must be one of {allowed}")
                elif param_type == "boolean":
                    if not isinstance(value, bool):
                        raise ProcessError(f"Invalid type for {param}: expected boolean")

        except ProcessError:
            raise
        except Exception as e:
            raise ProcessError(f"Parameter validation failed: {e}")

    async def _execute_move(self, parameters: Dict[str, Any]) -> None:
        """Execute move action.
        
        Args:
            parameters: Move parameters
            
        Raises:
            ProcessError: If move fails
        """
        try:
            position = parameters.get("position")
            if not position:
                raise ProcessError("Move position not specified")
                
            self._hardware_state["motion_active"] = True
            await self._comm_service.move_to_position(position)
            self._hardware_state["last_position"] = position
            self._hardware_state["motion_active"] = False
            
        except HardwareError as e:
            self._hardware_state["motion_active"] = False
            raise ProcessError(f"Move action failed: {e}", {"device": e.device})
        except Exception as e:
            self._hardware_state["motion_active"] = False
            raise ProcessError(f"Move action failed: {e}")

    async def _execute_spray(self, parameters: Dict[str, Any]) -> None:
        """Execute spray action.
        
        Args:
            parameters: Spray parameters
            
        Raises:
            ProcessError: If spray fails
        """
        try:
            duration = parameters.get("duration")
            if duration is None:
                raise ProcessError("Spray duration not specified")

            self._hardware_state["spray_active"] = True
            await self._comm_service.start_spray()
            self._hardware_state["last_spray_state"] = True
            
            await self._message_broker.wait(duration)
            
            await self._comm_service.stop_spray()
            self._hardware_state["spray_active"] = False
            self._hardware_state["last_spray_state"] = False
            
        except Exception as e:
            try:
                await self._comm_service.stop_spray()
            except Exception:
                pass
            self._hardware_state["spray_active"] = False
            self._hardware_state["last_spray_state"] = False
            raise ProcessError(f"Spray action failed: {e}")

    async def _execute_pause(self, parameters: Dict[str, Any]) -> None:
        """Execute pause action.
        
        Args:
            parameters: Pause parameters
            
        Raises:
            ProcessError: If pause fails
        """
        try:
            duration = parameters.get("duration")
            if duration is None:
                raise ProcessError("Pause duration not specified")
            await self._message_broker.wait(duration)
        except Exception as e:
            raise ProcessError(f"Pause action failed: {e}")

    async def _execute_custom_action(self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Execute custom action via messaging API.
        
        Args:
            action_type: Custom action type
            parameters: Action parameters
            
        Raises:
            ProcessError: If custom action fails
        """
        try:
            response = await self._message_broker.request(
                f"action/{action_type}",
                parameters
            )
            if response.get("status") != "success":
                raise ProcessError(
                    "Custom action failed",
                    {"error": response.get("error")}
                )
        except Exception as e:
            raise ProcessError(f"Custom action failed: {e}")

    async def _reset_hardware_state(self) -> None:
        """Reset hardware to safe state.
        
        This is called during cleanup and abort operations.
        """
        try:
            # Stop spray if active
            if self._hardware_state.get("spray_active"):
                try:
                    await self._comm_service.stop_spray()
                except Exception as e:
                    logger.error(f"Error stopping spray during reset: {e}")
                self._hardware_state["spray_active"] = False
                self._hardware_state["last_spray_state"] = False

            # Stop motion if active
            if self._hardware_state.get("motion_active"):
                try:
                    await self._comm_service.abort_operation()
                except Exception as e:
                    logger.error(f"Error stopping motion during reset: {e}")
                self._hardware_state["motion_active"] = False

            # Reset state tracking
            self._hardware_state.update({
                "spray_active": False,
                "motion_active": False,
                "last_position": None,
                "last_spray_state": None
            })

        except Exception as e:
            logger.error(f"Error resetting hardware state: {e}")
            # Don't re-raise, this is cleanup code
