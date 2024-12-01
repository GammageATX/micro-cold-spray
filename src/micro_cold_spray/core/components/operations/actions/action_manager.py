"""Action management component."""
from typing import Dict, Any, List
from loguru import logger
import asyncio
from datetime import datetime

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.config.config_manager import ConfigManager
from ...process.validation.process_validator import ProcessValidator
from ....exceptions import (
    OperationError,
    ValidationError
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
            raise OperationError("Action manager initialization failed", "action", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def shutdown(self) -> None:
        """Shutdown action manager."""
        try:
            # Cancel any active validations
            for validation in self._active_validations.values():
                validation.cancel()
            logger.info("Action manager shutdown complete")
        except Exception as e:
            logger.exception("Error during action manager shutdown")
            raise OperationError(
                "Action manager shutdown failed", "shutdown", {
                    "error": str(e), "timestamp": datetime.now().isoformat()})

    async def execute_action(self, action_name: str,
                             parameters: Dict[str, Any]) -> None:
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
            raise OperationError("Action execution failed", "execute", {
                "action": action_name,
                "error": str(e),
                "parameters": parameters
            })

    async def execute_action_group(
            self, group_name: str, parameters: Dict[str, Any]) -> None:
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
            raise OperationError("Action group execution failed", "group", {
                "group": group_name,
                "error": str(e),
                "parameters": parameters
            })

    async def _execute_atomic_action(
            self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Execute atomic action from process.yaml."""
        try:
            # Get action definition
            action_def = await self._get_action_definition(action_type)
            logger.debug(
                f"Executing atomic action {action_type} with parameters {parameters}")

            # Validate action parameters
            await self._validate_action(action_type, parameters)

            # Send messages defined in action
            for message in action_def["messages"]:
                message_data = self._substitute_parameters(
                    parameters, message["data"])

                # Convert to proper message format
                msg_payload = {
                    "topic": message["topic"],
                    "data": {
                        "tag": str(message_data["tag"]),
                        "value": message_data.get("value", True)
                    }
                }

                await self._message_broker.publish(message["topic"], msg_payload)

                # Wait for validation response if needed
                if "validation" in message:
                    await self._handle_validation(message["validation"])

            # Handle validations if defined
            if "validation" in action_def:
                for validation in action_def["validation"]:
                    await self._handle_validation(validation)

        except Exception as e:
            logger.error(f"Error in atomic action {action_type}: {e}")
            raise OperationError("Action execution failed", "action", {
                "action": action_type,
                "parameters": parameters,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_validation(self, validation_def: Dict[str, Any]) -> None:
        """Handle validation checks."""
        try:
            # Convert string validation to dict if needed
            if isinstance(validation_def, str):
                validation_def = {"tag": validation_def}

            result = await self._process_validator.validate_condition(validation_def)
            if not result["valid"]:
                raise ValidationError(f"Validation failed: {result['errors']}")

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise ValidationError(f"Validation failed: {str(e)}") from e

    async def _check_requirements(
        self,
        requirements: List[Dict[str, Any]],
        parameters: Dict[str, Any]
    ) -> None:
        """Check if requirements are met before action."""
        try:
            for req in requirements:
                if "parameter_file" in req:
                    if "parameter_file" not in parameters:
                        raise ValidationError(
                            "Parameter file required but not provided")
                elif "pattern_file" in req:
                    if "pattern_file" not in parameters:
                        raise ValidationError(
                            "Pattern file required but not provided")

        except Exception as e:
            raise ValidationError(
                f"Requirements check failed: {
                    str(e)}") from e

    async def _get_action_definition(self, action_type: str) -> Dict[str, Any]:
        """Get action definition from process config."""
        try:
            # Parse action path (e.g. 'gas.set_main_flow')
            action_path = action_type.split('.')
            process_config = await self._config_manager.get_config("process")
            current = process_config.get("atomic_actions", {})

            # Navigate to action definition
            for part in action_path:
                current = current[part]
            return current

        except KeyError as e:
            raise ValidationError(
                f"Action {action_type} not found in config") from e
        except Exception as e:
            raise ValidationError(
                f"Error getting action definition: {
                    str(e)}") from e

    def _substitute_parameters(
        self,
        parameters: Dict[str, Any],
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Substitute parameters into template values."""
        try:
            if isinstance(template, dict):
                result = {}
                for key, value in template.items():
                    if isinstance(value, str) and value.startswith(
                            "{") and value.endswith("}"):
                        param_path = value[1:-1].split(".")
                        current = parameters
                        for part in param_path:
                            current = current[part]
                        result[key] = current
                    else:
                        result[key] = value
                return result
            return template

        except KeyError as e:
            raise ValidationError(
                f"Parameter substitution failed - missing key: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Parameter substitution failed: {str(e)}")

    async def _handle_time_delay(self, delay_def: Dict[str, Any]) -> None:
        """Handle time delay steps."""
        try:
            delay = self._process_config["time_delays"][delay_def]["delay"]
            logger.debug(f"Waiting for {delay} seconds")
            await asyncio.sleep(delay)
        except KeyError as e:
            raise ValidationError(f"Time delay definition not found: {str(e)}")
        except Exception as e:
            raise OperationError("Time delay failed", "delay", {
                "delay_def": delay_def,
                "error": str(e)
            })

    async def _handle_error(self, error: Exception,
                            context: Dict[str, Any]) -> None:
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
            raise OperationError("Error handler failed", "action", {
                "error": str(e),
                "original_error": str(error),
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_action_request(self, data: Dict[str, Any]) -> None:
        """Handle action request messages."""
        try:
            action_type = data.get("action")
            parameters = data.get("parameters", {})

            if "group" in data:
                await self.execute_action_group(data["group"], parameters)
            elif action_type is not None:
                await self.execute_action(action_type, parameters)
            else:
                raise ValidationError("Missing action type in request")
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

    async def _validate_action(
            self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Validate action parameters against rules."""
        try:
            # Get validation rules from process config
            process_config = await self._config_manager.get_config("process")
            validation_rules = process_config.get(
                "validation", {}).get("actions", {})

            # Get action definition
            action_def = await self._get_action_definition(action_type)

            # Check required parameters
            if "required_fields" in validation_rules:
                required = validation_rules["required_fields"]["fields"]
                for field in required:
                    if field not in parameters:
                        raise ValidationError(
                            validation_rules["required_fields"]["message"])

            # Check for unknown parameters
            if "optional_fields" in validation_rules:
                optional = validation_rules["optional_fields"]["fields"]
                for field in parameters:
                    if field not in required and field not in optional:
                        raise ValidationError(
                            validation_rules["optional_fields"]["message"])

            # Validate motion parameters if present
            if action_type.startswith("motion."):
                await self._validate_motion_action(action_type, parameters)

            # Validate against action-specific rules
            if "validation" in action_def:
                for validation in action_def["validation"]:
                    await self._handle_validation(validation)
        except Exception as e:
            logger.error(f"Action validation failed: {e}")
            raise ValidationError(f"Action validation failed: {str(e)}") from e

    async def _validate_motion_action(
            self, action_type: str, parameters: Dict[str, Any]) -> None:
        """Validate motion action parameters."""
        try:
            hardware_config = await self._config_manager.get_config("hardware")
            stage_dims = hardware_config["physical"]["stage"]["dimensions"]

            # Extract position parameters
            position = {}
            for axis in ('x', 'y', 'z'):
                if axis in parameters:
                    position[axis] = parameters[axis]

            # Validate against stage dimensions
            for axis, value in position.items():
                if value < 0 or value > stage_dims[axis]:
                    msg = (
                        f"{axis.upper()} position {value} exceeds "
                        f"stage dimensions [0, {stage_dims[axis]}]"
                    )
                    raise ValidationError(msg)
        except Exception as e:
            logger.error(f"Motion action validation failed: {e}")
            raise ValidationError(
                f"Motion action validation failed: {
                    str(e)}") from e
