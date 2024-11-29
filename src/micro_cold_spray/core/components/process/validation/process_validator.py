"""Process validation component."""
from typing import Dict, Any, Optional, TypedDict
from loguru import logger
import asyncio
from datetime import datetime

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.config.config_manager import ConfigManager
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
        """Handle validation request."""
        try:
            validation_type = data.get("type")
            validation_data = data.get("data", {})
            
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }
            
            if validation_type == "parameters":
                validation_result = await self.validate_parameters(validation_data)
            elif validation_type == "pattern":
                validation_result = await self.validate_pattern(
                    validation_data.get("type"),
                    validation_data.get("pattern_data", {})
                )
            elif validation_type == "hardware_sets":
                validation_result = await self.validate_hardware_set(validation_data)
            else:
                validation_result["errors"].append(f"Unknown validation type: {validation_type}")
                validation_result["valid"] = False
            
            # Always publish validation response
            await self._message_broker.publish(
                "validation/response",
                {
                    "type": validation_type,
                    "result": validation_result,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error validating parameters: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "context": "validation",
                "timestamp": datetime.now().isoformat()
            })

    async def validate_parameters(self, parameters: Dict[str, Any]) -> ValidationResult:
        """Validate process parameters against configuration limits."""
        try:
            # Get safety limits from hardware config
            hw_config = self._config_manager.get_config("hardware")
            safety_limits = hw_config.get("safety", {})
            
            validation_result: ValidationResult = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

            # Validate gas parameters
            if "gas" in parameters:
                gas_params = parameters["gas"]
                gas_limits = safety_limits.get("gas", {})
                
                # Validate main flow
                if "main_flow" in gas_params:
                    flow = gas_params["main_flow"]
                    flow_limits = gas_limits.get("main_flow", {})
                    if flow < flow_limits.get("min", 0):
                        validation_result["errors"].append(
                            f"Main flow too low: {flow} (min {flow_limits['min']})"
                        )
                        validation_result["valid"] = False
                    elif flow > flow_limits.get("max", 100):
                        validation_result["errors"].append(
                            f"Main flow too high: {flow} (max {flow_limits['max']})"
                        )
                        validation_result["valid"] = False
                    elif flow < flow_limits.get("warning", 0):
                        validation_result["warnings"].append(
                            f"Main flow low: {flow} (warning at {flow_limits['warning']})"
                        )

                # Validate feeder flow
                if "feeder_flow" in gas_params:
                    flow = gas_params["feeder_flow"]
                    flow_limits = gas_limits.get("feeder_flow", {})
                    if flow < flow_limits.get("min", 0):
                        validation_result["errors"].append(
                            f"Feeder flow too low: {flow} (min {flow_limits['min']})"
                        )
                        validation_result["valid"] = False
                    elif flow > flow_limits.get("max", 10):
                        validation_result["errors"].append(
                            f"Feeder flow too high: {flow} (max {flow_limits['max']})"
                        )
                        validation_result["valid"] = False

            # Validate powder parameters
            if "powder" in parameters:
                powder_params = parameters["powder"]
                powder_limits = safety_limits.get("powder", {})
                
                if "feeder" in powder_params:
                    feeder = powder_params["feeder"]
                    feeder_limits = powder_limits.get("feeder", {})
                    
                    # Validate feeder frequency
                    if "frequency" in feeder:
                        freq = feeder["frequency"]
                        freq_limits = feeder_limits.get("frequency", {})
                        if freq < freq_limits.get("min", 0):
                            validation_result["errors"].append(
                                f"Feeder frequency too low: {freq} (min {freq_limits['min']})"
                            )
                            validation_result["valid"] = False
                        elif freq > freq_limits.get("max", 1000):
                            validation_result["errors"].append(
                                f"Feeder frequency too high: {freq} (max {freq_limits['max']})"
                            )
                            validation_result["valid"] = False

                    # Validate deagglomerator
                    if "deagglomerator" in feeder:
                        deagg = feeder["deagglomerator"]
                        deagg_limits = feeder_limits.get("deagglomerator", {})
                        
                        if "duty_cycle" in deagg:
                            duty = deagg["duty_cycle"]
                            duty_limits = deagg_limits.get("duty_cycle", {})
                            if duty < duty_limits.get("min", 0):
                                validation_result["errors"].append(
                                    f"Duty cycle too low: {duty} (min {duty_limits['min']})"
                                )
                                validation_result["valid"] = False
                            elif duty > duty_limits.get("max", 100):
                                validation_result["errors"].append(
                                    f"Duty cycle too high: {duty} (max {duty_limits['max']})"
                                )
                                validation_result["valid"] = False

            # Publish validation response
            await self._message_broker.publish(
                "validation/response",
                {
                    "type": "parameters",
                    "result": validation_result,
                    "timestamp": datetime.now().isoformat()
                }
            )

            return validation_result

        except Exception as e:
            logger.error(f"Parameter validation error: {e}")
            raise ValidationError(f"Parameter validation failed: {str(e)}") from e

    async def validate_pattern(self, pattern_type: str, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern configuration."""
        try:
            pattern_config = self._config_manager.get_config("patterns")
            hw_config = self._config_manager.get_config("hardware")
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
            
            # Validate required parameters
            required_params = pattern_def.get("required_parameters", [])
            for param in required_params:
                if param not in pattern_data:
                    validation_results["errors"].append(
                        f"Missing required parameter: {param}"
                    )
                    validation_results["valid"] = False
            
            # Validate parameter ranges
            param_limits = pattern_def.get("parameter_limits", {})
            for param, value in pattern_data.items():
                if param in param_limits:
                    limits = param_limits[param]
                    if value < limits.get("min", float("-inf")):
                        validation_results["errors"].append(
                            f"{param} below minimum limit: {value} < {limits['min']}"
                        )
                        validation_results["valid"] = False
                    if value > limits.get("max", float("inf")):
                        validation_results["errors"].append(
                            f"{param} above maximum limit: {value} > {limits['max']}"
                        )
                        validation_results["valid"] = False
            
            # Validate sprayable area
            if "origin" in pattern_data:
                sprayable = hw_config.get("physical", {}).get("substrate_holder", {}).get("dimensions", {}).get("sprayable", {})
                x, y = pattern_data["origin"]
                
                # Get sprayable dimensions
                width = sprayable.get("width", 0)
                height = sprayable.get("height", 0)
                
                # Check if origin is within sprayable area
                if x < 0 or x > width:
                    validation_results["errors"].append(
                        f"Pattern origin X ({x}) exceeds sprayable area (0 to {width})"
                    )
                    validation_results["valid"] = False
                if y < 0 or y > height:
                    validation_results["errors"].append(
                        f"Pattern origin Y ({y}) exceeds sprayable area (0 to {height})"
                    )
                    validation_results["valid"] = False
                
                # Check if pattern extent exceeds sprayable area
                if "length" in pattern_data:
                    length = pattern_data["length"]
                    if x + length > width:
                        validation_results["errors"].append(
                            f"Pattern extent ({x + length}) exceeds sprayable area width ({width})"
                        )
                        validation_results["valid"] = False
            
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
            
            # Get sequence rules
            rules = sequence_config.get("rules", {})
            required_steps = rules.get("required_steps", [])
            step_order = rules.get("step_order", {})
            
            # Validate required steps
            steps = sequence_data.get("steps", [])
            step_names = [step.get("action") for step in steps]
            
            for required in required_steps:
                if required not in step_names:
                    validation_results["errors"].append(
                        f"Missing required step: {required}"
                    )
                    validation_results["valid"] = False
            
            # Validate step order
            for i, step in enumerate(steps[:-1]):
                current_action = step.get("action")
                next_action = steps[i+1].get("action")
                
                if current_action in step_order:
                    valid_next = step_order[current_action]
                    if next_action not in valid_next:
                        validation_results["errors"].append(
                            f"Invalid step order: {current_action} -> {next_action}"
                        )
                        validation_results["valid"] = False
            
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
        state_data: Dict[str, Any],
        process_config: Dict[str, Any],
        validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate process parameters against current state."""
        try:
            # Get process validation rules
            rules = process_config.get("validation", {})
            
            # Validate gas flow stability
            if "gas_flow_stable" in rules:
                flow_rule = rules["gas_flow_stable"]
                tolerance = flow_rule.get("tolerance", 0.1)
                
                # Check main flow
                main_flow = state_data.get("gas_control.main_flow.measured", 0.0)
                main_setpoint = state_data.get("gas_control.main_flow.setpoint", 0.0)
                if abs(main_flow - main_setpoint) > tolerance:
                    validation_results["errors"].append(
                        f"Main gas flow unstable: {main_flow} vs {main_setpoint}"
                    )
                
                # Check feeder flow
                feeder_flow = state_data.get("gas_control.feeder_flow.measured", 0.0)
                feeder_setpoint = state_data.get("gas_control.feeder_flow.setpoint", 0.0)
                if abs(feeder_flow - feeder_setpoint) > tolerance:
                    validation_results["errors"].append(
                        f"Feeder gas flow unstable: {feeder_flow} vs {feeder_setpoint}"
                    )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Process validation error: {e}")
            raise ValidationError(f"Process validation failed: {str(e)}") from e

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

    async def validate_hardware_set(self, hardware_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hardware set configuration."""
        try:
            hw_config = self._config_manager.get_config("hardware")
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Get hardware sets config
            hardware_sets = hw_config.get("physical", {}).get("hardware_sets", {})
            active_set = hardware_data.get("active_set")
            
            if not active_set:
                validation_result["errors"].append("No active hardware set specified")
                validation_result["valid"] = False
                return validation_result
            
            if active_set not in hardware_sets:
                validation_result["errors"].append(f"Unknown hardware set: {active_set}")
                validation_result["valid"] = False
                return validation_result
            
            # Get set configuration
            set_config = hardware_sets[active_set]
            components = hardware_data.get("components", {})
            
            # Validate each component matches the set
            for component_type in ["nozzle", "feeder", "deagglomerator"]:
                component = components.get(component_type)
                expected = set_config.get(component_type)
                
                if not component:
                    validation_result["errors"].append(
                        f"Missing {component_type} specification for hardware set {active_set}"
                    )
                    validation_result["valid"] = False
                    continue
                
                if component != expected:
                    validation_result["errors"].append(
                        f"{component_type} {component} does not match hardware set {active_set} (expected {expected})"
                    )
                    validation_result["valid"] = False
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Hardware set validation error: {e}")
            raise ValidationError(f"Hardware set validation failed: {str(e)}") from e

    async def validate_condition(self, validation_def: Dict[str, Any]) -> ValidationResult:
        """Validate a condition based on tag value."""
        try:
            validation_result: ValidationResult = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Get tag to validate
            tag = validation_def.get("tag")
            if not tag:
                validation_result["errors"].append("No tag specified for validation")
                validation_result["valid"] = False
                return validation_result
            
            # Get expected value/condition if specified
            expected_value = validation_def.get("value")
            condition = validation_def.get("condition", "equals")
            
            # Request current tag value
            response = await self._message_broker.request(
                "tag/get",
                {
                    "tag": tag,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            if not response:
                validation_result["errors"].append(f"No response for tag: {tag}")
                validation_result["valid"] = False
                return validation_result
            
            current_value = response.get("value")
            
            # Validate based on condition
            if expected_value is not None:
                if condition == "equals":
                    if current_value != expected_value:
                        validation_result["errors"].append(
                            f"Tag {tag} value {current_value} does not equal {expected_value}"
                        )
                        validation_result["valid"] = False
                elif condition == "greater_than":
                    if current_value <= expected_value:
                        validation_result["errors"].append(
                            f"Tag {tag} value {current_value} not greater than {expected_value}"
                        )
                        validation_result["valid"] = False
                elif condition == "less_than":
                    if current_value >= expected_value:
                        validation_result["errors"].append(
                            f"Tag {tag} value {current_value} not less than {expected_value}"
                        )
                        validation_result["valid"] = False
                else:
                    validation_result["errors"].append(f"Unknown condition: {condition}")
                    validation_result["valid"] = False
                
            return validation_result
            
        except Exception as e:
            logger.error(f"Condition validation error: {e}")
            raise ValidationError(f"Condition validation failed: {str(e)}") from e