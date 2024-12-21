"""Sequence validator."""

from typing import Dict, Any, List
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.validation.validators.base_validator import (
    check_required_fields,
    check_unknown_fields,
    check_numeric_range,
    check_enum_value,
    check_timestamp
)
from micro_cold_spray.api.validation.validators.hardware_validator import HardwareValidator


class SequenceValidator:
    """Validator for spray sequences."""

    def __init__(
        self,
        validation_rules: Dict[str, Any],
        message_broker: MessagingService
    ):
        """Initialize sequence validator.
        
        Args:
            validation_rules: Validation rules from config
            message_broker: Message broker for hardware checks
        """
        self._rules = validation_rules
        self._message_broker = message_broker
        self._hardware_validator = HardwareValidator(validation_rules, message_broker)

    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sequence data.
        
        Args:
            data: Sequence data to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        try:
            # Check required fields first
            required = self._rules["sequences"]["required_fields"]
            required_errors = check_required_fields(
                data,
                required["fields"],
                "Sequence: "
            )
            if required_errors:
                return {
                    "valid": False,
                    "errors": required_errors,
                    "warnings": warnings
                }

            # Validate metadata
            if "metadata" in data:
                metadata_errors = await self._validate_metadata(data["metadata"])
                errors.extend(metadata_errors)

            # Validate steps
            if "steps" in data:
                # Check max steps first
                max_steps = self._rules["sequences"].get("max_steps", 100)
                if len(data["steps"]) > max_steps:
                    errors.append(f"Sequence exceeds maximum steps: {len(data['steps'])} > {max_steps}")
                else:
                    # Validate each step
                    for i, step in enumerate(data["steps"]):
                        step_errors = await self._validate_sequence_step(step)
                        errors.extend([f"Step {i+1}: {err}" for err in step_errors])

            # Validate sequence type rules
            if "type" in data:
                type_errors = await self._validate_sequence_type(data)
                errors.extend(type_errors)

            # Validate safety conditions
            if "safety" in self._rules["sequences"]:
                safety_errors = await self._validate_safety_conditions()
                errors.extend(safety_errors)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Sequence validation failed: {e}")
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Sequence validation failed: {str(e)}"
            )

    async def _validate_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Validate sequence metadata.
        
        Args:
            metadata: Metadata to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            # Check required fields
            required = ["name", "version", "created"]
            errors.extend(check_required_fields(
                metadata,
                required,
                "Metadata: "
            ))
            
            # Validate created timestamp
            if "created" in metadata:
                error = check_timestamp(
                    metadata["created"],
                    field_name="Created timestamp"
                )
                if error:
                    errors.append(f"Metadata: {error}")
                    
        except Exception as e:
            errors.append(f"Metadata validation error: {str(e)}")
        return errors

    async def _validate_sequence_step(self, step: Dict[str, Any]) -> List[str]:
        """Validate sequence step.
        
        Args:
            step: Step data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["sequences"]["step_fields"]
            
            # Check required fields
            errors.extend(check_required_fields(
                step,
                rules["required_fields"]["fields"]
            ))
            
            # Check for unknown fields
            if "optional_fields" in rules:
                valid_fields = (
                    rules["required_fields"]["fields"] +
                    rules["optional_fields"]["fields"]
                )
                errors.extend(check_unknown_fields(
                    step,
                    valid_fields
                ))
            
            # Validate step type-specific fields
            if "action" in step:
                action_errors = await self._validate_action_step(step)
                errors.extend(action_errors)
            elif "pattern" in step:
                pattern_errors = await self._validate_pattern_step(step)
                errors.extend(pattern_errors)
                
        except Exception as e:
            errors.append(f"Step validation error: {str(e)}")
        return errors

    async def _validate_sequence_type(self, data: Dict[str, Any]) -> List[str]:
        """Validate sequence type rules.
        
        Args:
            data: Sequence data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            sequence_type = data["type"]
            type_rules = self._rules["sequences"]["types"].get(sequence_type)
            
            if not type_rules:
                errors.append(f"Unknown sequence type: {sequence_type}")
                return errors
            
            # Check required steps first
            if "required_steps" in type_rules:
                required_steps = type_rules["required_steps"]
                found_steps = set()
                
                for step in data["steps"]:
                    if "action" in step:
                        found_steps.add(step["action"])
                
                missing_steps = []
                for required in required_steps:
                    if required not in found_steps:
                        missing_steps.append(required)
                        errors.append(f"Missing required step: {required}")
                
                # Only check step order if all required steps are present
                if not missing_steps and type_rules.get("check_order", False):
                    order_errors = self._validate_step_order(
                        data["steps"],
                        type_rules["step_order"],
                        type_rules.get("optional_steps", [])
                    )
                    errors.extend(order_errors)
                    
        except Exception as e:
            errors.append(f"Sequence type validation error: {str(e)}")
        return errors

    async def _validate_safety_conditions(self) -> List[str]:
        """Validate safety conditions.
        
        Returns:
            List of error messages
        """
        try:
            # Use hardware validator for safety checks
            result = await self._hardware_validator.validate({})
            return result.get("errors", [])
        except Exception as e:
            logger.error(f"Safety validation failed: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Safety validation failed: {str(e)}"
            )

    def _validate_step_order(
        self,
        steps: List[Dict[str, Any]],
        expected_order: List[str],
        optional_steps: List[str]
    ) -> List[str]:
        """Validate step order.
        
        Args:
            steps: List of sequence steps
            expected_order: Expected order of steps
            optional_steps: Optional steps that can be skipped
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            # Extract step actions in order
            step_actions = []
            for step in steps:
                if "action" in step:
                    step_actions.append(step["action"])

            # Check each required step is in correct order
            last_found_idx = -1
            for expected in expected_order:
                if expected in step_actions:
                    idx = step_actions.index(expected)
                    if idx < last_found_idx:
                        errors.append(f"Step order violation: {expected} found out of order")
                    last_found_idx = idx
                elif expected not in optional_steps:
                    errors.append(f"Step order violation: {expected} not found in expected position")

        except Exception as e:
            errors.append(f"Step order validation error: {str(e)}")
        return errors

    async def _validate_action_step(self, step: Dict[str, Any]) -> List[str]:
        """Validate action step.
        
        Args:
            step: Step data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            action = step["action"]
            parameters = step.get("parameters", {})
            
            # Check action type is valid
            valid_actions = self._rules["sequences"].get("valid_actions", [])
            error = check_enum_value(
                action,
                valid_actions,
                field_name="Action type"
            )
            if error:
                errors.append(error)
                return errors
            
            # Validate action parameters
            if "parameters" in step:
                param_rules = self._rules["sequences"]["actions"][action]
                
                # Check required parameters
                if "required_parameters" in param_rules:
                    errors.extend(check_required_fields(
                        parameters,
                        param_rules["required_parameters"],
                        f"Action {action}: "
                    ))
                
                # Check parameter values
                if "parameter_rules" in param_rules:
                    for param_name, param_value in parameters.items():
                        if param_name in param_rules["parameter_rules"]:
                            rule = param_rules["parameter_rules"][param_name]
                            
                            if "min" in rule or "max" in rule:
                                error = check_numeric_range(
                                    param_value,
                                    min_val=rule.get("min"),
                                    max_val=rule.get("max"),
                                    field_name=f"{action} {param_name}"
                                )
                                if error:
                                    errors.append(f"Action {action}: {error}")
                                    
                            elif "values" in rule:
                                error = check_enum_value(
                                    param_value,
                                    rule["values"],
                                    field_name=f"{action} {param_name}"
                                )
                                if error:
                                    errors.append(f"Action {action}: {error}")
                    
        except Exception as e:
            errors.append(f"Action validation error: {str(e)}")
        return errors

    async def _validate_pattern_step(self, step: Dict[str, Any]) -> List[str]:
        """Validate pattern step.
        
        Args:
            step: Step data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            pattern = step["pattern"]
            
            # Check pattern type is valid
            valid_patterns = self._rules["sequences"].get("valid_patterns", [])
            error = check_enum_value(
                pattern["type"],
                valid_patterns,
                field_name="Pattern type"
            )
            if error:
                errors.append(error)
                return errors
            
            # Validate pattern parameters
            if "parameters" in pattern:
                param_rules = self._rules["sequences"]["patterns"][pattern["type"]]
                
                # Check required parameters
                if "required_parameters" in param_rules:
                    errors.extend(check_required_fields(
                        pattern["parameters"],
                        param_rules["required_parameters"],
                        f"Pattern {pattern['type']}: "
                    ))
                
                # Check parameter values
                if "parameter_rules" in param_rules:
                    for param_name, param_value in pattern["parameters"].items():
                        if param_name in param_rules["parameter_rules"]:
                            rule = param_rules["parameter_rules"][param_name]
                            
                            if "min" in rule or "max" in rule:
                                error = check_numeric_range(
                                    param_value,
                                    min_val=rule.get("min"),
                                    max_val=rule.get("max"),
                                    field_name=f"{pattern['type']} {param_name}"
                                )
                                if error:
                                    errors.append(f"Pattern {pattern['type']}: {error}")
                                    
                            elif "values" in rule:
                                error = check_enum_value(
                                    param_value,
                                    rule["values"],
                                    field_name=f"{pattern['type']} {param_name}"
                                )
                                if error:
                                    errors.append(f"Pattern {pattern['type']}: {error}")
                    
        except Exception as e:
            errors.append(f"Pattern validation error: {str(e)}")
        return errors
