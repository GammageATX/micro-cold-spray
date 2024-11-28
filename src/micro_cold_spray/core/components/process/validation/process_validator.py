"""Process validation component."""
from typing import Dict, Any, Optional, TypedDict
from loguru import logger
import asyncio
from datetime import datetime

from ....infrastructure.messaging.message_broker import MessageBroker
from ....config.config_manager import ConfigManager
from ....exceptions import ValidationError

class ValidationResult(TypedDict):
    """Type definition for validation results."""
    valid: bool
    errors: list[str]
    warnings: list[str]
    timestamp: str

class ProcessValidator:
    """Validates process parameters and configurations."""
    
    def __init__(self, message_broker: MessageBroker, config_manager: ConfigManager):
        """Initialize validator with required dependencies."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._is_initialized = False
        
        logger.info("Process validator initialized")

    async def initialize(self) -> None:
        """Initialize validator."""
        try:
            if self._is_initialized:
                return

            # Subscribe to validation requests - using standard topic
            await self._message_broker.subscribe(
                "validation/request",
                self._handle_validation_request
            )
            
            self._is_initialized = True
            logger.info("Process validator initialization complete")
            
        except Exception as e:
            logger.exception("Failed to initialize process validator")
            raise ValidationError(f"Process validator initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown validator."""
        try:
            self._is_initialized = False
            logger.info("Process validator shutdown complete")
            
        except Exception as e:
            logger.exception("Error during process validator shutdown")
            raise ValidationError(f"Process validator shutdown failed: {str(e)}") from e

    async def _handle_validation_request(self, data: Dict[str, Any]) -> None:
        """Handle validation requests."""
        try:
            validation_type = data.get("type")
            if not validation_type:
                await self._message_broker.publish("error", {
                    "error": "No validation type provided",
                    "context": "validation_request",
                    "timestamp": datetime.now().isoformat()
                })
                return

            # Route to appropriate validation method
            if validation_type == "parameters":
                result = await self.validate_parameters(data.get("parameters", {}))
            elif validation_type == "pattern":
                result = await self.validate_pattern(data.get("pattern_type"), data.get("pattern_data", {}))
            elif validation_type == "sequence":
                result = await self.validate_sequence(data.get("sequence_data", {}))
            else:
                await self._message_broker.publish("error", {
                    "error": f"Unknown validation type: {validation_type}",
                    "context": "validation_request",
                    "timestamp": datetime.now().isoformat()
                })
                return

            # Publish validation result
            await self._message_broker.publish(
                "validation/response",
                {
                    "result": result,
                    "request_id": data.get("request_id"),
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error validating parameters: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "context": "parameter_validation",
                "parameters": data.get("parameters"),
                "topic": "validation/request",
                "timestamp": datetime.now().isoformat()
            })

    async def validate_parameters(self, parameters: Dict[str, Any]) -> ValidationResult:
        """Validate process parameters against configuration limits."""
        try:
            # Get safety limits from hardware config
            hw_config = self._config_manager.get_config("hardware")
            safety_limits = hw_config["safety"]["gas"]
            
            validation_result: ValidationResult = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Validate gas pressures
            if "main_pressure" in parameters:
                main_pressure = parameters["main_pressure"]
                if main_pressure < safety_limits["main_pressure"]["min"]:
                    validation_result["errors"].append(
                        f"Main pressure too low: {main_pressure} PSI (min {safety_limits['main_pressure']['min']} PSI)"
                    )
                    validation_result["valid"] = False
                elif main_pressure < safety_limits["main_pressure"]["warning"]:
                    validation_result["warnings"].append(
                        f"Main pressure low: {main_pressure} PSI (warning at {safety_limits['main_pressure']['warning']} PSI)"
                    )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Parameter validation error: {e}")
            raise ValidationError(f"Parameter validation failed: {str(e)}") from e

    async def validate_pattern(self, pattern_type: str, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern configuration."""
        try:
            pattern_config = self._config_manager.get_config("patterns")
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Get pattern type definition
            pattern_def = pattern_config.get("types", {}).get(pattern_type)
            if not pattern_def:
                validation_results["errors"].append(f"Unknown pattern type: {pattern_type}")
                validation_results["valid"] = False
                return validation_results
            
            # Validate pattern parameters
            required_params = pattern_def.get("required_parameters", [])
            for param in required_params:
                if param not in pattern_data:
                    validation_results["errors"].append(
                        f"Missing required parameter: {param}"
                    )
            
            # Validate parameter ranges
            param_limits = pattern_def.get("parameter_limits", {})
            for param, value in pattern_data.items():
                if param in param_limits:
                    limits = param_limits[param]
                    if value < limits.get("min", float("-inf")):
                        validation_results["errors"].append(
                            f"{param} below minimum limit"
                        )
                    if value > limits.get("max", float("inf")):
                        validation_results["errors"].append(
                            f"{param} above maximum limit"
                        )
            
            validation_results["valid"] = len(validation_results["errors"]) == 0
            return validation_results
            
        except Exception as e:
            logger.error(f"Pattern validation error: {e}")
            raise ValidationError(f"Pattern validation failed: {str(e)}") from e

    async def validate_sequence(self, sequence_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sequence configuration."""
        try:
            sequence_config = self._config_manager.get_config("sequences")
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Validate sequence structure
            if "steps" not in sequence_data:
                validation_results["errors"].append("Missing steps in sequence")
                validation_results["valid"] = False
                return validation_results
            
            # Validate each step
            for i, step in enumerate(sequence_data["steps"]):
                if "action" not in step:
                    validation_results["errors"].append(
                        f"Missing action in step {i}"
                    )
                if "parameters" not in step:
                    validation_results["errors"].append(
                        f"Missing parameters in step {i}"
                    )
                    
                # Validate step parameters
                if "parameters" in step:
                    await self._validate_step_parameters(
                        step["action"],
                        step["parameters"],
                        validation_results
                    )
            
            validation_results["valid"] = len(validation_results["errors"]) == 0
            return validation_results
            
        except Exception as e:
            logger.error(f"Sequence validation error: {e}")
            raise ValidationError(f"Sequence validation failed: {str(e)}") from e

    async def _validate_motion_params(
        self,
        motion_params: Dict[str, Any],
        config: Dict[str, Any],
        results: Dict[str, Any]
    ) -> None:
        """Validate motion-related parameters."""
        try:
            limits = config.get('limits', {}).get('motion', {})
            
            # Validate axis
            axis = motion_params.get('axis')
            if axis not in ['x', 'y', 'z']:
                results["errors"].append(f"Invalid axis: {axis}")
                
            # Validate position limits
            for axis, limits in limits.items():
                if axis in motion_params:
                    position = motion_params[axis]
                    if position < limits.get('min', float('-inf')):
                        results["errors"].append(
                            f"{axis} position {position} below minimum {limits['min']}"
                        )
                    if position > limits.get('max', float('inf')):
                        results["errors"].append(
                            f"{axis} position {position} above maximum {limits['max']}"
                        )
                        
            # Validate velocity
            velocity = motion_params.get('velocity')
            if velocity is not None:
                vel_limits = limits.get('velocity', {})
                if velocity < vel_limits.get('min', 0):
                    results["errors"].append("Velocity below minimum limit")
                if velocity > vel_limits.get('max', float('inf')):
                    results["errors"].append("Velocity above maximum limit")
                    
        except Exception as e:
            logger.error(f"Error validating motion parameters: {e}")
            results["errors"].append(f"Motion validation error: {str(e)}")

    async def _validate_process_params(
        self,
        process_params: Dict[str, Any],
        config: Dict[str, Any],
        results: Dict[str, Any]
    ) -> None:
        """Validate process-related parameters."""
        try:
            limits = config.get("limits", {}).get("process", {})
            
            for param, value in process_params.items():
                param_limits = limits.get(param, {})
                if param_limits:
                    if value < param_limits.get("min", float("-inf")):
                        results["errors"].append(
                            f"{param} below minimum limit {param_limits['min']}"
                        )
                    if value > param_limits.get("max", float("inf")):
                        results["errors"].append(
                            f"{param} above maximum limit {param_limits['max']}"
                        )
                        
        except Exception as e:
            logger.error(f"Error validating process parameters: {e}")
            results["errors"].append(f"Process validation error: {str(e)}")

    async def _validate_step_parameters(
        self,
        action: str,
        parameters: Dict[str, Any],
        results: Dict[str, Any]
    ) -> None:
        """Validate sequence step parameters."""
        try:
            action_config = self._config_manager.get_config("actions")
            action_def = action_config.get("actions", {}).get(action)
            
            if not action_def:
                results["errors"].append(f"Unknown action type: {action}")
                return
                
            # Validate required parameters
            required_params = action_def.get("required_parameters", [])
            for param in required_params:
                if param not in parameters:
                    results["errors"].append(
                        f"Missing required parameter {param} for action {action}"
                    )
                    
            # Validate parameter ranges
            param_limits = action_def.get("parameter_limits", {})
            for param, value in parameters.items():
                if param in param_limits:
                    limits = param_limits[param]
                    if value < limits.get("min", float("-inf")):
                        results["errors"].append(
                            f"{param} below minimum limit for action {action}"
                        )
                    if value > limits.get("max", float("inf")):
                        results["errors"].append(
                            f"{param} above maximum limit for action {action}"
                        )
                        
        except Exception as e:
            logger.error(f"Error validating step parameters: {e}")
            results["errors"].append(f"Step validation error: {str(e)}")