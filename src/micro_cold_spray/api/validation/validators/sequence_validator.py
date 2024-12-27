"""Sequence validator implementation."""

from typing import Dict, Any, List
from loguru import logger
from fastapi import status

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.validation.validators.base_validator import (
    check_required_fields,
    check_unknown_fields,
    check_numeric_range,
    check_enum_value,
    check_timestamp,
    get_validation_rules
)


class SequenceValidator:
    """Validator for sequence configurations."""

    def __init__(self, validation_rules: Dict[str, Any]):
        """Initialize sequence validator.
        
        Args:
            validation_rules: Validation rules from config
        """
        self._rules = validation_rules

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
        try:
            errors = []
            warnings = []
            
            # Get sequence rules
            sequence_rules = get_validation_rules(self._rules, "sequences")
            if not sequence_rules:
                logger.warning("No sequence validation rules found")
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": ["No sequence validation rules configured"]
                }

            # Check required fields
            if "required_fields" in sequence_rules:
                errors.extend(check_required_fields(
                    data,
                    sequence_rules["required_fields"]["fields"],
                    sequence_rules["required_fields"]["message"]
                ))

            # Check unknown fields
            if "optional_fields" in sequence_rules:
                warnings.extend(check_unknown_fields(
                    data,
                    sequence_rules["required_fields"]["fields"] + sequence_rules["optional_fields"]["fields"],
                    sequence_rules["optional_fields"]["message"]
                ))

            # Validate metadata if present
            if "metadata" in data:
                metadata_errors = self._validate_metadata(data["metadata"])
                errors.extend(metadata_errors)

            # Validate steps if present
            if "steps" in data:
                step_errors = await self._validate_steps(data["steps"])
                errors.extend(step_errors)

            # Validate sequence type rules
            if "type" in data:
                type_errors = await self._validate_sequence_type(data)
                errors.extend(type_errors)

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

    def _validate_metadata(self, metadata: Dict[str, Any]) -> List[str]:
        """Validate sequence metadata.
        
        Args:
            metadata: Metadata to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            metadata_rules = get_validation_rules(self._rules, "sequences", "metadata")
            
            # Check required fields
            if "required_fields" in metadata_rules:
                errors.extend(check_required_fields(
                    metadata,
                    metadata_rules["required_fields"]["fields"],
                    metadata_rules["required_fields"]["message"]
                ))

            # Check unknown fields
            if "optional_fields" in metadata_rules:
                errors.extend(check_unknown_fields(
                    metadata,
                    metadata_rules["required_fields"]["fields"] + metadata_rules["optional_fields"]["fields"],
                    metadata_rules["optional_fields"]["message"]
                ))

            # Validate timestamp if present
            if "timestamp" in metadata:
                error = check_timestamp(metadata["timestamp"])
                if error:
                    errors.append(error)

        except Exception as e:
            errors.append(f"Metadata validation error: {str(e)}")
        return errors

    async def _validate_steps(self, steps: List[Dict[str, Any]]) -> List[str]:
        """Validate sequence steps.
        
        Args:
            steps: List of steps to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            step_rules = get_validation_rules(self._rules, "sequences", "step_fields")
            
            # Check max steps
            max_steps = get_validation_rules(self._rules, "sequences").get("max_steps")
            if max_steps and len(steps) > max_steps:
                errors.append(f"Sequence exceeds maximum steps ({max_steps})")
                return errors

            # Validate each step
            for i, step in enumerate(steps):
                # Check required fields
                if "required_fields" in step_rules:
                    errors.extend(check_required_fields(
                        step,
                        step_rules["required_fields"]["fields"],
                        f"Step {i+1}: {step_rules['required_fields']['message']}"
                    ))

                # Check unknown fields
                if "optional_fields" in step_rules:
                    errors.extend(check_unknown_fields(
                        step,
                        step_rules["required_fields"]["fields"] + step_rules["optional_fields"]["fields"],
                        f"Step {i+1}: {step_rules['optional_fields']['message']}"
                    ))

                # Validate step action
                if "action" in step:
                    action_errors = await self._validate_step_action(step)
                    errors.extend([f"Step {i+1}: {err}" for err in action_errors])

        except Exception as e:
            errors.append(f"Step validation error: {str(e)}")
        return errors

    async def _validate_step_action(self, step: Dict[str, Any]) -> List[str]:
        """Validate step action.
        
        Args:
            step: Step data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            action = step["action"]
            parameters = step.get("parameters", {})

            # Validate based on action type
            if action == "move":
                errors.extend(await self._validate_move_step(parameters))
            elif action == "spray":
                errors.extend(await self._validate_spray_step(parameters))
            elif action == "pattern":
                errors.extend(await self._validate_pattern_step(parameters))
            else:
                errors.append(f"Unknown action type: {action}")

        except Exception as e:
            errors.append(f"Action validation error: {str(e)}")
        return errors

    async def _validate_move_step(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate move step parameters.
        
        Args:
            parameters: Step parameters to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            move_rules = get_validation_rules(self._rules, "sequences", "move")
            
            # Check required parameters
            if "required_parameters" in move_rules:
                errors.extend(check_required_fields(
                    parameters,
                    move_rules["required_parameters"]["fields"],
                    move_rules["required_parameters"]["message"]
                ))

            # Validate position limits
            if "position_limits" in move_rules:
                for axis, limits in move_rules["position_limits"].items():
                    if axis in parameters:
                        error = check_numeric_range(
                            parameters[axis],
                            min_val=limits.get("min"),
                            max_val=limits.get("max"),
                            field_name=f"{axis} position"
                        )
                        if error:
                            errors.append(error)

        except Exception as e:
            errors.append(f"Move validation error: {str(e)}")
        return errors

    async def _validate_spray_step(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate spray step parameters.
        
        Args:
            parameters: Step parameters to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            spray_rules = get_validation_rules(self._rules, "sequences", "spray")
            
            # Check required parameters
            if "required_parameters" in spray_rules:
                errors.extend(check_required_fields(
                    parameters,
                    spray_rules["required_parameters"]["fields"],
                    spray_rules["required_parameters"]["message"]
                ))

            # Validate spray parameters
            if "parameter_limits" in spray_rules:
                for param, limits in spray_rules["parameter_limits"].items():
                    if param in parameters:
                        error = check_numeric_range(
                            parameters[param],
                            min_val=limits.get("min"),
                            max_val=limits.get("max"),
                            field_name=param
                        )
                        if error:
                            errors.append(error)

        except Exception as e:
            errors.append(f"Spray validation error: {str(e)}")
        return errors

    async def _validate_pattern_step(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate pattern step parameters.
        
        Args:
            parameters: Step parameters to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            pattern_rules = get_validation_rules(self._rules, "sequences", "patterns")
            
            # Check pattern type
            if "type" not in parameters:
                errors.append("Pattern type not specified")
                return errors

            pattern_type = parameters["type"]
            if pattern_type not in pattern_rules:
                errors.append(f"Unknown pattern type: {pattern_type}")
                return errors

            type_rules = pattern_rules[pattern_type]
            
            # Check required parameters
            if "required_parameters" in type_rules:
                errors.extend(check_required_fields(
                    parameters,
                    type_rules["required_parameters"]["fields"],
                    type_rules["required_parameters"]["message"]
                ))

            # Validate parameter values
            if "parameter_limits" in type_rules:
                for param, limits in type_rules["parameter_limits"].items():
                    if param in parameters:
                        error = check_numeric_range(
                            parameters[param],
                            min_val=limits.get("min"),
                            max_val=limits.get("max"),
                            field_name=param
                        )
                        if error:
                            errors.append(error)

        except Exception as e:
            errors.append(f"Pattern validation error: {str(e)}")
        return errors

    async def _validate_sequence_type(self, data: Dict[str, Any]) -> List[str]:
        """Validate sequence type specific rules.
        
        Args:
            data: Sequence data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            sequence_type = data["type"]
            type_rules = get_validation_rules(self._rules, "sequences", "types", sequence_type)
            
            if not type_rules:
                errors.append(f"Unknown sequence type: {sequence_type}")
                return errors

            # Validate type specific rules
            if "rules" in type_rules:
                for rule in type_rules["rules"]:
                    # Add type specific validation here
                    pass

        except Exception as e:
            errors.append(f"Sequence type validation error: {str(e)}")
        return errors
