"""Pattern validator implementation."""

from typing import Dict, Any, List
from loguru import logger
from fastapi import status

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.validation.validators.base_validator import (
    check_required_fields,
    check_unknown_fields,
    check_numeric_range,
    check_enum_value,
    get_validation_rules
)


class PatternValidator:
    """Validator for pattern configurations."""

    def __init__(self, validation_rules: Dict[str, Any]):
        """Initialize pattern validator.
        
        Args:
            validation_rules: Validation rules from config
        """
        self._rules = validation_rules

    async def validate(self, pattern_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern configuration.
        
        Args:
            pattern_type: Type of pattern to validate
            data: Pattern configuration to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        try:
            errors = []
            warnings = []
            
            # Get pattern rules
            pattern_rules = get_validation_rules(self._rules, "patterns", pattern_type)
            if not pattern_rules:
                logger.warning(f"No validation rules found for pattern type: {pattern_type}")
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": [f"No validation rules configured for pattern type: {pattern_type}"]
                }

            # Check required fields
            if "required_fields" in pattern_rules:
                errors.extend(check_required_fields(
                    data,
                    pattern_rules["required_fields"]["fields"],
                    pattern_rules["required_fields"]["message"]
                ))

            # Check unknown fields
            if "optional_fields" in pattern_rules:
                warnings.extend(check_unknown_fields(
                    data,
                    pattern_rules["required_fields"]["fields"] + pattern_rules["optional_fields"]["fields"],
                    pattern_rules["optional_fields"]["message"]
                ))

            # Validate dimensions if present
            if "dimensions" in pattern_rules and "dimensions" in data:
                dimension_errors = self._validate_dimensions(
                    data["dimensions"],
                    pattern_rules["dimensions"]
                )
                errors.extend(dimension_errors)

            # Validate parameters if present
            if "parameters" in pattern_rules and "parameters" in data:
                parameter_errors = self._validate_parameters(
                    data["parameters"],
                    pattern_rules["parameters"]
                )
                errors.extend(parameter_errors)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Pattern validation failed: {e}")
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Pattern validation failed: {str(e)}"
            )

    def _validate_dimensions(self, dimensions: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """Validate pattern dimensions.
        
        Args:
            dimensions: Dimension data to validate
            rules: Validation rules for dimensions
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            # Check required fields
            if "required_fields" in rules:
                errors.extend(check_required_fields(
                    dimensions,
                    rules["required_fields"]["fields"],
                    rules["required_fields"]["message"]
                ))

            # Check unknown fields
            if "optional_fields" in rules:
                errors.extend(check_unknown_fields(
                    dimensions,
                    rules["required_fields"]["fields"] + rules["optional_fields"]["fields"],
                    rules["optional_fields"]["message"]
                ))

            # Validate dimension values
            if "limits" in rules:
                for dim, limits in rules["limits"].items():
                    if dim in dimensions:
                        error = check_numeric_range(
                            dimensions[dim],
                            min_val=limits.get("min"),
                            max_val=limits.get("max"),
                            field_name=f"Dimension {dim}"
                        )
                        if error:
                            errors.append(error)

        except Exception as e:
            errors.append(f"Dimension validation error: {str(e)}")
        return errors

    def _validate_parameters(self, parameters: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """Validate pattern parameters.
        
        Args:
            parameters: Parameter data to validate
            rules: Validation rules for parameters
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            # Check required fields
            if "required_fields" in rules:
                errors.extend(check_required_fields(
                    parameters,
                    rules["required_fields"]["fields"],
                    rules["required_fields"]["message"]
                ))

            # Check unknown fields
            if "optional_fields" in rules:
                errors.extend(check_unknown_fields(
                    parameters,
                    rules["required_fields"]["fields"] + rules["optional_fields"]["fields"],
                    rules["optional_fields"]["message"]
                ))

            # Validate parameter values
            if "limits" in rules:
                for param, limits in rules["limits"].items():
                    if param in parameters:
                        error = check_numeric_range(
                            parameters[param],
                            min_val=limits.get("min"),
                            max_val=limits.get("max"),
                            field_name=f"Parameter {param}"
                        )
                        if error:
                            errors.append(error)

            # Validate enum values
            if "enum_values" in rules:
                for param, values in rules["enum_values"].items():
                    if param in parameters:
                        error = check_enum_value(
                            parameters[param],
                            values["values"],
                            field_name=f"Parameter {param}"
                        )
                        if error:
                            errors.append(error)

        except Exception as e:
            errors.append(f"Parameter validation error: {str(e)}")
        return errors
