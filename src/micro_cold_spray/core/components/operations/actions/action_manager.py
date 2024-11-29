"""Action management component."""
from typing import Dict, Any, List, Union
from loguru import logger
import asyncio
from datetime import datetime

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.config.config_manager import ConfigManager
from ...process.validation.process_validator import ProcessValidator
from ....exceptions import (
    ActionError,
    ActionConfigError,
    ActionExecutionError,
    ActionValidationError,
    ActionTimeoutError,
    ActionRequirementError,
    ActionParameterError
)

class ActionManager:
    """Manages execution of atomic actions and action groups"""

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        process_validator: ProcessValidator
    ) -> None:
        """Initialize action manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._process_validator = process_validator
        self._active_validations = {}
        logger.debug("Action manager initialized")

    async def initialize(self) -> None:
        """Initialize action manager."""
        try:
            # Load process config
            self._process_config = await self._config_manager.get_config("process")
            
            # Subscribe to action topics
            await self._message_broker.subscribe("action/request", self._handle_action_request)
            await self._message_broker.subscribe("action/cancel", self._handle_action_cancel)
            
            logger.info("Action manager initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize action manager: {e}")
            raise ActionError(f"Action manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown action manager."""
        try:
            # Cancel any active validations
            for validation in self._active_validations.values():
                validation.cancel()
                
            logger.info("Action manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during action manager shutdown")
            raise ActionError(f"Action manager shutdown failed: {str(e)}") from e

    async def execute_action(self, action_name: str, parameters: Dict[str, Any]) -> None:
        """Execute a single atomic action."""
        try:
            logger.debug(f"Executing atomic action: {action_name}")
            await self._execute_atomic_action(action_name, parameters)
            
        except Exception as e:
            logger.error(f"Error executing action {action_name}: {e}")
            await self._handle_error(e, {
                "action": action_name,
                "parameters": parameters
            })
            raise ActionExecutionError(f"Action execution failed: {str(e)}") from e

    async def execute_action_group(self, group_name: str, parameters: Dict[str, Any]) -> None:
        """Execute an action group sequence."""
        try:
            logger.debug(f"Executing action group: {group_name}")
            
            # Get group definition
            group_def = self._process_config["action_groups"][group_name]
            
            # Check requirements
            if "requires" in group_def:
                await self._check_requirements(group_def["requires"], parameters)
                
            # Execute steps
            for step in group_def["steps"]:
                if "action" in step:
                    await self._execute_atomic_action(
                        step["action"],
                        self._substitute_parameters(parameters, step.get("parameters", {}))
                    )
                elif "validation" in step:
                    await self._handle_validation(step["validation"])
                elif "time_delay" in step:
                    await self._handle_time_delay(step["time_delay"])
                    
            logger.debug(f"Action group {group_name} completed")
            
        except Exception as e:
            logger.error(f"Error executing action group {group_name}: {e}")
            await self._handle_error(e, {
                "group": group_name,
                "parameters": parameters
            })
            raise ActionExecutionError(f"Action group execution failed: {str(e)}") from e

    async def _execute_atomic_action(self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Execute atomic action from process.yaml."""
        try:
            # Get action definition
            action_def = self._get_action_definition(action_type)
            logger.debug(f"Executing atomic action {action_type} with parameters {parameters}")
            
            # Send messages defined in action
            for message in action_def["messages"]:
                # Substitute parameters into message data
                message_data = self._substitute_parameters(parameters, message["data"])
                
                # Send message
                await self._message_broker.publish(
                    message["topic"],
                    message_data
                )
                    
            # Handle validations if defined
            if "validation" in action_def:
                for validation in action_def["validation"]:
                    await self._handle_validation(validation)
                    
        except Exception as e:
            logger.error(f"Error in atomic action {action_type}: {e}")
            raise ActionExecutionError(f"Atomic action failed: {str(e)}") from e

    async def _handle_validation(self, validation_def: Dict[str, Any]) -> None:
        """Handle validation checks."""
        try:
            result = await self._process_validator.validate_condition(validation_def)
            if not result["valid"]:
                raise ActionValidationError(f"Validation failed: {result['errors']}")
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise ActionValidationError(f"Validation failed: {str(e)}") from e

    async def _check_requirements(self, requirements: List[Dict[str, Any]], parameters: Dict[str, Any]) -> None:
        """Check if requirements are met before action."""
        try:
            for req in requirements:
                if "parameter_file" in req:
                    if "parameter_file" not in parameters:
                        raise ActionRequirementError("Parameter file required but not provided")
                elif "pattern_file" in req:
                    if "pattern_file" not in parameters:
                        raise ActionRequirementError("Pattern file required but not provided")
                        
        except Exception as e:
            raise ActionRequirementError(f"Requirements check failed: {str(e)}") from e

    def _get_action_definition(self, action_type: str) -> Dict[str, Any]:
        """Get action definition from process config."""
        try:
            # Parse action path (e.g. 'gas.set_main_flow')
            action_path = action_type.split('.')
            current = self._process_config["atomic_actions"]
            
            # Navigate to action definition
            for part in action_path:
                current = current[part]
            return current
            
        except KeyError as e:
            raise ActionConfigError(f"Action {action_type} not found in config") from e
        except Exception as e:
            raise ActionConfigError(f"Error getting action definition: {str(e)}") from e

    def _substitute_parameters(self, parameters: Dict[str, Any], template: Union[List[Dict[str, Any]], Dict[str, Any]]) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Substitute parameters into template values."""
        try:
            # Handle list template (common for message data)
            if isinstance(template, list):
                result = []
                for item in template:
                    if isinstance(item, dict):
                        # Process each dictionary in the list
                        processed_item = {}
                        for key, value in item.items():
                            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                                # Handle parameter reference
                                param_path = value[1:-1].split(".")
                                current = parameters
                                for part in param_path:
                                    current = current[part]
                                processed_item[key] = current
                            else:
                                # Use direct value
                                processed_item[key] = value
                        result.append(processed_item)
                    else:
                        # Non-dictionary items pass through unchanged
                        result.append(item)
                return result
            
            # Handle dictionary template
            elif isinstance(template, dict):
                result = {}
                for key, value in template.items():
                    if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                        # Handle parameter reference
                        param_path = value[1:-1].split(".")
                        current = parameters
                        for part in param_path:
                            current = current[part]
                        result[key] = current
                    else:
                        # Use direct value
                        result[key] = value
                return result
            
            else:
                raise ActionParameterError(f"Invalid template type: {type(template)}")

        except KeyError as e:
            raise ActionParameterError(f"Parameter substitution failed - missing key: {str(e)}") from e
        except Exception as e:
            raise ActionParameterError(f"Parameter substitution failed: {str(e)}") from e

    async def _handle_time_delay(self, delay_def: Dict[str, Any]) -> None:
        """Handle time delay steps."""
        try:
            delay = self._process_config["time_delays"][delay_def]["delay"]
            logger.debug(f"Waiting for {delay} seconds")
            await asyncio.sleep(delay)
            
        except KeyError as e:
            raise ActionConfigError(f"Time delay definition not found: {str(e)}") from e
        except Exception as e:
            raise ActionExecutionError(f"Time delay failed: {str(e)}") from e

    async def _handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle and publish errors."""
        try:
            error_data = {
                "error": str(error),
                "context": context,
                "timestamp": datetime.now().isoformat()
            }
            await self._message_broker.publish("action/error", error_data)
            logger.error(f"Action error: {error_data}")
            
        except Exception as e:
            logger.exception("Error handling action error")
            raise ActionError(f"Error handler failed: {str(e)}") from e

    async def _handle_action_request(self, data: Dict[str, Any]) -> None:
        """Handle action request messages."""
        try:
            action_type = data.get("action")
            parameters = data.get("parameters", {})
            
            if "group" in data:
                await self.execute_action_group(data["group"], parameters)
            else:
                await self.execute_action(action_type, parameters)
                
        except Exception as e:
            logger.error(f"Error handling action request: {e}")
            await self._handle_error(e, data)

    async def _handle_action_cancel(self, data: Dict[str, Any]) -> None:
        """Handle action cancellation requests."""
        try:
            # Cancel any active validations
            validation_id = data.get("validation_id")
            if validation_id in self._active_validations:
                self._active_validations[validation_id].cancel()
                del self._active_validations[validation_id]
                
            logger.info(f"Cancelled action: {data}")
            
        except Exception as e:
            logger.error(f"Error handling action cancel: {e}")
            await self._handle_error(e, data)