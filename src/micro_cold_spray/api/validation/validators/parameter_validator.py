"""Parameter validator."""

from typing import Dict, Any, List
from loguru import logger
from fastapi import status

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.validation.validators.base_validator import (
    check_required_fields,
    check_unknown_fields,
    check_numeric_range,
    check_enum_value
)


class ParameterValidator:
    """Validator for parameter configurations."""

    def __init__(self, validation_rules: Dict[str, Any]):
        """Initialize parameter validator.
        
        Args:
            validation_rules: Validation rules from config
        """
        self._rules = validation_rules

    async def validate(self, parameter_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameter configuration.
        
        Args:
            parameter_type: Type of parameter to validate
            data: Parameter configuration to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        try:
            errors = []
            warnings = []
            
            # Get parameter rules
            parameter_rules = self._rules.get("validation", {}).get("parameters", {}).get(parameter_type, {})
            if not parameter_rules:
                logger.warning(f"No validation rules found for parameter type: {parameter_type}")
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": [f"No validation rules configured for parameter type: {parameter_type}"]
                }

            # Check required fields
            if "required_fields" in parameter_rules:
                errors.extend(check_required_fields(
                    data,
                    parameter_rules["required_fields"]["fields"],
                    parameter_rules["required_fields"]["message"]
                ))

            # Check unknown fields
            if "optional_fields" in parameter_rules:
                warnings.extend(check_unknown_fields(
                    data,
                    parameter_rules["required_fields"]["fields"] + parameter_rules["optional_fields"]["fields"],
                    parameter_rules["optional_fields"]["message"]
                ))

            # Validate parameter values
            if "parameter_limits" in parameter_rules:
                for param, limits in parameter_rules["parameter_limits"].items():
                    if param in data:
                        error = check_numeric_range(
                            data[param],
                            min_val=limits.get("min"),
                            max_val=limits.get("max"),
                            field_name=param
                        )
                        if error:
                            errors.append(error)

            # Validate enum values
            if "enum_values" in parameter_rules:
                for param, values in parameter_rules["enum_values"].items():
                    if param in data:
                        error = check_enum_value(
                            data[param],
                            values["values"],
                            field_name=param
                        )
                        if error:
                            errors.append(error)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Parameter validation failed: {e}")
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Parameter validation failed: {str(e)}"
            )
