"""Process validation component."""
from datetime import datetime
from typing import Any, Dict, List, TypedDict

from loguru import logger

from ....exceptions import ValidationError
from ....infrastructure.config.config_manager import ConfigManager
from ....infrastructure.messaging.message_broker import MessageBroker


class ValidationResult(TypedDict):
    """Type definition for validation results."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    timestamp: str


class ProcessValidator:
    """Process validation component."""

    def __init__(
            self,
            message_broker: MessageBroker,
            config_manager: ConfigManager):
        """Initialize validator with required dependencies."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._is_initialized = False

        logger.info("Process validator initialized")

    async def initialize(self) -> None:
        """Initialize process validator."""
        try:
            # Subscribe to validation requests
            await self._message_broker.subscribe(
                "validation/request",
                self._handle_validation_request
            )

            self._is_initialized = True
            logger.info("Process validator initialization complete")

        except Exception as e:
            logger.exception("Failed to initialize process validator")
            raise ValidationError("Process validator initialization failed", {
                "error": str(e)
            })

    async def shutdown(self) -> None:
        """Shutdown validator."""
        try:
            self._is_initialized = False
            logger.info("Process validator shutdown complete")

        except Exception as e:
            logger.exception("Error during process validator shutdown")
            raise ValidationError("Process validator shutdown failed", {
                "error": str(e)
            })

    async def _handle_validation_request(
            self, request: Dict[str, Any]) -> None:
        """Handle validation requests."""
        try:
            validation_type = request.get("type")
            validation_data = request.get("data", {})
            result = None

            if validation_type == "pattern":
                result = await self._validate_pattern(validation_data)
            elif validation_type == "hardware":
                result = await self._validate_hardware_state(validation_data)
            elif validation_type == "parameters":
                result = await self.validate_parameters(validation_data)
            else:
                result = {
                    "valid": False,
                    "errors": [f"Unknown validation type: {validation_type}"],
                    "warnings": [],
                    "timestamp": datetime.now().isoformat()
                }

            # Publish validation response
            await self._message_broker.publish(
                "validation/response",
                {
                    "result": result,
                    "request_type": validation_type,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Validation request failed: {e}")
            await self._message_broker.publish(
                "validation/response",
                {
                    "result": {
                        "valid": False,
                        "errors": [str(e)],
                        "warnings": [],
                        "timestamp": datetime.now().isoformat()
                    },
                    "request_type": request.get("type"),
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise ValidationError("Validation request failed", {
                "request": request,
                "error": str(e)
            })

    async def validate_parameters(
            self, parameters: Dict[str, Any]) -> ValidationResult:
        """Validate process parameters against configuration limits."""
        try:
            # Get configs
            process_config = await self._config_manager.get_config("process")
            validation_rules = process_config.get("validation", {}).get("parameters", {})

            validation_result = self._create_validation_result()

            # Validate each parameter group
            if "material" in parameters:
                material_result = await self._validate_material_parameters(
                    parameters["material"], validation_rules.get("material", {}))
                self._merge_validation_results(validation_result, material_result)

            if "process" in parameters:
                process_result = await self._validate_process_parameters(
                    parameters["process"], validation_rules.get("process", {}))
                self._merge_validation_results(validation_result, process_result)

            if "gas" in parameters:
                gas_result = await self._validate_gas_parameters(parameters["gas"])
                self._merge_validation_results(validation_result, gas_result)

            return validation_result

        except Exception as e:
            logger.error(f"Parameter validation failed: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

    def _create_validation_result(self) -> ValidationResult:
        """Create a new validation result object."""
        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "timestamp": datetime.now().isoformat()
        }

    def _merge_validation_results(
            self,
            target: ValidationResult,
            source: ValidationResult) -> None:
        """Merge source validation result into target."""
        target["valid"] &= source["valid"]
        target["errors"].extend(source["errors"])
        target["warnings"].extend(source["warnings"])

    async def _validate_material_parameters(
            self,
            material_params: Dict[str, Any],
            material_rules: Dict[str, Any]) -> ValidationResult:
        """Validate material parameters."""
        result = self._create_validation_result()
        required = material_rules.get("required_fields", {})
        optional = material_rules.get("optional_fields", {})

        # Check required fields
        for field in required.get("fields", []):
            if field not in material_params:
                result["errors"].append(required["message"])
                result["valid"] = False
                break

        # Check for unknown fields
        for field in material_params.keys():
            has_field = (
                field in required.get("fields", [])
                or field in optional.get("fields", [])
            )
            if not has_field:
                result["errors"].append(optional["message"])
                result["valid"] = False
                break

        return result

    async def _validate_process_parameters(
            self,
            process_params: Dict[str, Any],
            process_rules: Dict[str, Any]) -> ValidationResult:
        """Validate process parameters."""
        result = self._create_validation_result()
        required = process_rules.get("required_fields", {})
        optional = process_rules.get("optional_fields", {})

        # Check required fields
        for field in required.get("fields", []):
            if field not in process_params:
                result["errors"].append(required["message"])
                result["valid"] = False
                break

        # Check for unknown fields
        for field in process_params.keys():
            has_field = (
                field in required.get("fields", [])
                or field in optional.get("fields", [])
            )
            if not has_field:
                result["errors"].append(optional["message"])
                result["valid"] = False
                break

        return result

    async def _validate_gas_parameters(
            self,
            gas_params: Dict[str, Any]) -> ValidationResult:
        """Validate gas parameters against safety limits."""
        try:
            hw_config = await self._config_manager.get_config("hardware")
            gas_limits = hw_config.get("safety", {}).get("gas", {})
            result = self._create_validation_result()

            # Validate gas type
            if "type" in gas_params:
                gas_type = gas_params["type"]
                valid_types = gas_limits.get("valid_types", ["helium", "nitrogen"])
                if gas_type not in valid_types:
                    result["valid"] = False
                    result["errors"].append(
                        f"Invalid gas type: {gas_type}. Must be one of: {valid_types}"
                    )

            # Validate main flow
            if "main_flow" in gas_params:
                main_flow_result = self._validate_flow_parameter(
                    gas_params["main_flow"],
                    gas_limits.get("main_flow", {}),
                    "Main flow"
                )
                self._merge_validation_results(result, main_flow_result)

            # Validate carrier flow
            if "carrier_flow" in gas_params:
                carrier_flow_result = self._validate_flow_parameter(
                    gas_params["carrier_flow"],
                    gas_limits.get("carrier_flow", {}),
                    "Carrier flow"
                )
                self._merge_validation_results(result, carrier_flow_result)

            return result

        except Exception as e:
            logger.error(f"Gas parameter validation failed: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

    def _validate_flow_parameter(
            self,
            value: float,
            limits: Dict[str, float],
            name: str) -> ValidationResult:
        """Validate a flow parameter against limits."""
        result = self._create_validation_result()
        min_value = limits.get("min", 0.0)
        max_value = limits.get("max", float("inf"))

        if value < min_value:
            result["valid"] = False
            result["errors"].append(
                f"{name} ({value}) is below minimum limit ({min_value})"
            )
        elif value > max_value:
            result["valid"] = False
            result["errors"].append(
                f"{name} ({value}) is above maximum limit ({max_value})"
            )

        return result

    async def _validate_safety_limits(
            self,
            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters against safety limits."""
        try:
            validation_result = self._create_validation_result()

            # Validate gas parameters
            if "gas" in parameters:
                gas_result = await self._validate_gas_parameters(parameters["gas"])
                self._merge_validation_results(validation_result, gas_result)

            # Validate powder parameters
            if "powder" in parameters:
                powder_result = await self._validate_powder_parameters(parameters["powder"])
                self._merge_validation_results(validation_result, powder_result)

            return validation_result

        except Exception as e:
            logger.error(f"Safety limit validation failed: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

    async def _validate_powder_parameters(
            self,
            powder_params: Dict[str, Any]) -> ValidationResult:
        """Validate powder parameters against safety limits."""
        try:
            hw_config = await self._config_manager.get_config("hardware")
            powder_limits = hw_config.get("safety", {}).get("powder", {})
            result = self._create_validation_result()

            if "feeder" in powder_params:
                feeder_result = self._validate_feeder_parameter(
                    powder_params["feeder"],
                    powder_limits.get("feeder", {})
                )
                self._merge_validation_results(result, feeder_result)

            return result

        except Exception as e:
            logger.error(f"Powder parameter validation failed: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

    def _validate_feeder_parameter(
            self,
            feeder: float,
            limits: Dict[str, float]) -> ValidationResult:
        """Validate feeder parameter against its limits."""
        result = self._create_validation_result()

        if feeder < limits.get("min", 0):
            result["errors"].append(
                f"Feeder rate too low: {feeder} (min {limits['min']})"
            )
            result["valid"] = False
        elif feeder > limits.get("max", float('inf')):
            result["errors"].append(
                f"Feeder rate too high: {feeder} (max {limits['max']})"
            )
            result["valid"] = False
        elif feeder < limits.get("warning", float('inf')):
            result["warnings"].append(
                f"Feeder rate near minimum: {feeder} (warning {limits['warning']})"
            )

        return result

    async def validate_pattern(
        self,
        pattern_type: str,
        pattern_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate pattern configuration."""
        try:
            pattern_config = await self._config_manager.get_config("patterns")
            hw_config = await self._config_manager.get_config("hardware")
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

            # Get pattern type definition
            pattern_def = pattern_config.get("types", {}).get(pattern_type)
            if not pattern_def:
                validation_results["errors"].append(
                    f"Unknown pattern type: {pattern_type}")
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
                substrate = hw_config.get(
                    "physical", {}).get(
                    "substrate_holder", {})
                dimensions = substrate.get("dimensions", {})
                sprayable = dimensions.get("sprayable", {})
                x, y = pattern_data["origin"]

                # Get sprayable dimensions
                width = sprayable.get("width", 0)
                height = sprayable.get("height", 0)

                # Check if origin is within sprayable area
                if x < 0 or x > width:
                    validation_results["errors"].append(
                        f"Pattern origin X ({x}) exceeds sprayable area (0 to {width})")
                    validation_results["valid"] = False
                if y < 0 or y > height:
                    validation_results["errors"].append(
                        f"Pattern origin Y ({y}) exceeds sprayable area (0 to {height})")
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
            raise ValidationError(
                f"Pattern validation failed: {
                    str(e)}") from e

    async def validate_sequence(
            self, sequence_data: Dict[str, Any]) -> ValidationResult:
        """Validate sequence against rules."""
        try:
            # Get validation rules
            process_config = await self._config_manager.get_config("process")
            validation_rules = process_config.get(
                "validation", {}).get("sequences", {})

            validation_result: ValidationResult = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

            # Check required sequence fields
            required_fields = validation_rules.get("required_fields", {})
            for field in required_fields.get("fields", []):
                if field not in sequence_data:
                    validation_result["errors"].append(
                        required_fields["message"])
                    validation_result["valid"] = False
                    break

            # Validate each step
            if "steps" in sequence_data:
                step_rules = validation_rules.get("step_fields", {})

                for i, step in enumerate(sequence_data["steps"]):
                    # Check required step fields
                    required = step_rules.get("required_fields", {})
                    for field in required.get("fields", []):
                        if field not in step:
                            validation_result["errors"].append(
                                f"Step {i + 1}: {required['message']}"
                            )
                            validation_result["valid"] = False
                            break

                    # Check for unknown fields
                    optional = step_rules.get("optional_fields", {})
                    for field in step.keys():
                        if (
                            field not in required.get("fields", [])
                            and field not in optional.get("fields", [])
                        ):
                            validation_result["errors"].append(
                                f"Step {i + 1}: {optional['message']}"
                            )
                            validation_result["valid"] = False
                            break

            return validation_result

        except Exception as e:
            logger.error(f"Sequence validation error: {e}")
            raise ValidationError("Sequence validation failed", {
                "sequence": sequence_data,
                "error": str(e)
            })

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
                            f"{axis} position {position} below minimum {
                                limits['min']}")
                    if position > limits.get('max', float('inf')):
                        results["errors"].append(
                            f"{axis} position {position} above maximum {
                                limits['max']}")

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
            # Get process validation rules - no need to await dict
            rules = process_config.get("validation", {})

            # Validate gas flow stability
            if "gas_flow_stable" in rules:
                flow_rule = rules["gas_flow_stable"]
                tolerance = flow_rule.get("tolerance", 0.1)

                # Check main flow
                main_flow = state_data.get(
                    "gas_control.main_flow.measured", 0.0)
                main_setpoint = state_data.get(
                    "gas_control.main_flow.setpoint", 0.0)
                if abs(main_flow - main_setpoint) > tolerance:
                    validation_results["errors"].append(
                        f"Main gas flow unstable: {main_flow} vs {main_setpoint}")

                # Check feeder flow
                feeder_flow = state_data.get(
                    "gas_control.feeder_flow.measured", 0.0)
                feeder_setpoint = state_data.get(
                    "gas_control.feeder_flow.setpoint", 0.0)
                if abs(feeder_flow - feeder_setpoint) > tolerance:
                    validation_results["errors"].append(
                        f"Feeder gas flow unstable: {feeder_flow} vs {feeder_setpoint}")

            validation_results["timestamp"] = datetime.now().isoformat()
            return validation_results

        except Exception as e:
            logger.error(f"Process validation error: {e}")
            raise ValidationError(
                f"Process validation failed: {
                    str(e)}") from e

    async def _validate_step_parameters(
        self,
        action: str,
        parameters: Dict[str, Any],
        results: Dict[str, Any]
    ) -> None:
        """Validate sequence step parameters."""
        try:
            action_config = await self._config_manager.get_config("actions")
            action_def = action_config.get("actions", {}).get(action)

            if not action_def:
                results["errors"].append(f"Unknown action type: {action}")
                return

            # Validate required parameters
            required_params = action_def.get("required_parameters", [])
            for param in required_params:
                if param not in parameters:
                    results["errors"].append(
                        f"Missing required parameter {param} for action {action}")

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

    async def validate_hardware_set(
            self, hardware_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hardware set configuration."""
        try:
            hw_config = await self._config_manager.get_config("hardware")
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

            # Get hardware sets config
            hardware_sets = hw_config.get(
                "physical", {}).get(
                "hardware_sets", {})
            active_set = hardware_data.get("active_set")

            if not active_set:
                validation_result["errors"].append(
                    "No active hardware set specified")
                validation_result["valid"] = False
                return validation_result

            if active_set not in hardware_sets:
                validation_result["errors"].append(
                    f"Unknown hardware set: {active_set}")
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
                        f"Missing {component_type} specification for hardware set {active_set}")
                    validation_result["valid"] = False
                    continue

                if component != expected:
                    msg = (
                        f"{component_type} {component} does not match "
                        f"set definition {set_config[component_type]}"
                    )
                    validation_result["errors"].append(msg)
                    validation_result["valid"] = False

            return validation_result

        except Exception as e:
            logger.error(f"Hardware set validation error: {e}")
            raise ValidationError(
                f"Hardware set validation failed: {
                    str(e)}") from e

    async def validate_condition(
            self, validation_def: Dict[str, Any]) -> ValidationResult:
        """Validate process condition."""
        try:
            validation_result: ValidationResult = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

            # Get current value
            tag = validation_def.get("tag")
            condition = validation_def.get("condition", "equals")
            expected_value = validation_def.get("value")

            # Get current tag value
            response = await self._message_broker.request(
                "tag/get",
                {
                    "tag": tag,
                    "timestamp": datetime.now().isoformat()
                }
            )
            current_value = response.get("value")

            # Validate based on condition
            if expected_value is not None:
                if condition == "equals":
                    if current_value != expected_value:
                        validation_result["errors"].append(
                            f"Tag {tag} value {current_value} does not equal {expected_value}")
                        validation_result["valid"] = False
                elif condition == "greater_than":
                    if current_value <= expected_value:
                        validation_result["errors"].append(
                            f"Tag {tag} value {current_value} not greater than {expected_value}")
                        validation_result["valid"] = False
                elif condition == "less_than":
                    if current_value >= expected_value:
                        validation_result["errors"].append(
                            f"Tag {tag} value {current_value} not less than {expected_value}")
                        validation_result["valid"] = False
                else:
                    validation_result["errors"].append(
                        f"Unknown condition: {condition}")
                    validation_result["valid"] = False

            return validation_result

        except Exception as e:
            logger.error(f"Condition validation error: {e}")
            raise ValidationError("Condition validation failed", {
                "condition": validation_def,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _validate_pattern(
            self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern against process rules."""
        try:
            errors = []

            # Get hardware limits from correct path
            hardware_config = await self._config_manager.get_config("hardware")
            if not hardware_config.get(
                    "physical",
                    {}).get(
                    "stage",
                    {}).get("dimensions"):
                raise ValidationError(
                    "No stage dimensions defined in hardware config", {
                        "timestamp": datetime.now().isoformat()})

            stage_dims = hardware_config["physical"]["stage"]["dimensions"]

            # Validate pattern bounds
            pattern = pattern_data.get("pattern", {})
            pattern_type = pattern.get("type")
            pattern_params = pattern.get("params", {})

            if pattern_type == "serpentine":
                origin = pattern_params.get("origin", [0, 0])
                length = pattern_params.get("length", 0)

                # Check if pattern exceeds stage dimensions
                if (
                    origin[0] < 0 or origin[0] + length > stage_dims["x"]
                    or origin[1] < 0 or origin[1] > stage_dims["y"]
                ):
                    errors.append(
                        f"Pattern exceeds stage dimensions: "
                        f"[0, {stage_dims['x']}] x [0, {stage_dims['y']}]"
                    )

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Pattern validation failed: {e}")
            raise ValidationError("Pattern validation failed", {
                "pattern": pattern_data,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _validate_hardware_state(
            self, hardware_state: Dict[str, Any]) -> ValidationResult:
        """Validate hardware state."""
        try:
            result = self._create_validation_result()

            # Check connection
            if not hardware_state.get("connection", False):
                result["valid"] = False
                result["errors"].append("Hardware not connected")
                return result

            # Check for errors
            if hardware_state.get("error"):
                result["valid"] = False
                result["errors"].append(
                    f"Hardware error: {hardware_state['error']}")
                return result

            # Validate position
            position = hardware_state.get("position", {})
            if not position:
                result["valid"] = False
                result["errors"].append("Missing position data")
                return result

            # Get stage limits
            hw_config = await self._config_manager.get_config("hardware")
            stage_limits = hw_config.get("stage", {}).get("limits", {})

            # Check each axis
            for axis in ["x", "y", "z"]:
                if axis not in position:
                    result["valid"] = False
                    result["errors"].append(f"Missing {axis} position")
                    continue

                axis_pos = position[axis]
                axis_limits = stage_limits.get(axis, {})
                min_pos = axis_limits.get("min", float("-inf"))
                max_pos = axis_limits.get("max", float("inf"))

                if axis_pos < min_pos:
                    result["valid"] = False
                    result["errors"].append(
                        f"{axis.upper()} position ({axis_pos}) below minimum ({min_pos})"
                    )
                elif axis_pos > max_pos:
                    result["valid"] = False
                    result["errors"].append(
                        f"{axis.upper()} position ({axis_pos}) above maximum ({max_pos})"
                    )

            return result

        except Exception as e:
            logger.error(f"Hardware state validation failed: {e}")
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "timestamp": datetime.now().isoformat()
            }

    async def _validate_motion_limits(
            self, position: Dict[str, float]) -> None:
        """Validate motion position against stage dimensions."""
        try:
            hardware_config = await self._config_manager.get_config("hardware")
            stage_dims = hardware_config["physical"]["stage"]["dimensions"]

            # Check each axis
            for axis in ['x', 'y', 'z']:
                if axis in position:
                    value = position[axis]
                    if value < 0 or value > stage_dims[axis]:
                        msg = (
                            f"{axis.upper()} position {value} exceeds "
                            f"stage dimensions [0, {stage_dims[axis]}]"
                        )
                        raise ValidationError(
                            msg,
                            {
                                "position": position,
                                "axis": axis,
                                "value": value,
                                "limit": stage_dims[axis]
                            }
                        )
        except Exception as e:
            logger.error(f"Motion validation failed: {e}")
            raise ValidationError("Motion validation failed", {
                "position": position,
                "error": str(e)
            })
