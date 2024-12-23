"""Hardware validator."""

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


class HardwareValidator:
    """Validator for hardware configurations."""

    def __init__(self, validation_rules: Dict[str, Any]):
        """Initialize hardware validator.
        
        Args:
            validation_rules: Validation rules from config
        """
        self._rules = validation_rules

    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hardware configuration.
        
        Args:
            data: Hardware configuration to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        try:
            errors = []
            warnings = []
            
            # Get hardware rules
            hardware_rules = self._rules.get("validation", {}).get("hardware", {})
            if not hardware_rules:
                logger.warning("No hardware validation rules found")
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": ["No hardware validation rules configured"]
                }

            # Check required fields
            if "required_fields" in hardware_rules:
                errors.extend(check_required_fields(
                    data,
                    hardware_rules["required_fields"]["fields"],
                    hardware_rules["required_fields"]["message"]
                ))

            # Check unknown fields
            if "optional_fields" in hardware_rules:
                warnings.extend(check_unknown_fields(
                    data,
                    hardware_rules["required_fields"]["fields"] + hardware_rules["optional_fields"]["fields"],
                    hardware_rules["optional_fields"]["message"]
                ))

            # Validate components if present
            if "components" in hardware_rules:
                for component, rules in hardware_rules["components"].items():
                    if component in data:
                        component_errors = self._validate_component(
                            component,
                            data[component],
                            rules
                        )
                        errors.extend(component_errors)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Hardware validation failed: {e}")
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Hardware validation failed: {str(e)}"
            )

    def _validate_component(
        self,
        component: str,
        data: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> List[str]:
        """Validate hardware component.
        
        Args:
            component: Component name
            data: Component configuration data
            rules: Validation rules for component
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            # Check required fields
            if "required_fields" in rules:
                errors.extend(check_required_fields(
                    data,
                    rules["required_fields"]["fields"],
                    f"{component}: {rules['required_fields']['message']}"
                ))

            # Check unknown fields
            if "optional_fields" in rules:
                errors.extend(check_unknown_fields(
                    data,
                    rules["required_fields"]["fields"] + rules["optional_fields"]["fields"],
                    f"{component}: {rules['optional_fields']['message']}"
                ))

            # Validate parameter values
            if "parameter_limits" in rules:
                for param, limits in rules["parameter_limits"].items():
                    if param in data:
                        error = check_numeric_range(
                            data[param],
                            min_val=limits.get("min"),
                            max_val=limits.get("max"),
                            field_name=f"{component} {param}"
                        )
                        if error:
                            errors.append(error)

            # Validate enum values
            if "enum_values" in rules:
                for param, values in rules["enum_values"].items():
                    if param in data:
                        error = check_enum_value(
                            data[param],
                            values["values"],
                            field_name=f"{component} {param}"
                        )
                        if error:
                            errors.append(error)

        except Exception as e:
            errors.append(f"{component} validation error: {str(e)}")
        return errors
