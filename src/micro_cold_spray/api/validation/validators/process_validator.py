"""Process validator."""

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


class ProcessValidator:
    """Validator for process configurations."""

    def __init__(self, validation_rules: Dict[str, Any]):
        """Initialize process validator.
        
        Args:
            validation_rules: Validation rules from config
        """
        self._rules = validation_rules

    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate process configuration.
        
        Args:
            data: Process configuration to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        try:
            errors = []
            warnings = []
            
            # Get process rules
            process_rules = self._rules.get("validation", {}).get("process", {})
            if not process_rules:
                logger.warning("No process validation rules found")
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": ["No process validation rules configured"]
                }

            # Check required fields
            if "required_fields" in process_rules:
                errors.extend(check_required_fields(
                    data,
                    process_rules["required_fields"]["fields"],
                    process_rules["required_fields"]["message"]
                ))

            # Check unknown fields
            if "optional_fields" in process_rules:
                warnings.extend(check_unknown_fields(
                    data,
                    process_rules["required_fields"]["fields"] + process_rules["optional_fields"]["fields"],
                    process_rules["optional_fields"]["message"]
                ))

            # Validate parameters if present
            if "parameters" in process_rules:
                for param, rules in process_rules["parameters"].items():
                    if param in data:
                        param_errors = self._validate_parameter(
                            param,
                            data[param],
                            rules
                        )
                        errors.extend(param_errors)

            # Validate sequences if present
            if "sequences" in process_rules:
                for seq, rules in process_rules["sequences"].items():
                    if seq in data:
                        seq_errors = self._validate_sequence(
                            seq,
                            data[seq],
                            rules
                        )
                        errors.extend(seq_errors)

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            logger.error(f"Process validation failed: {e}")
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Process validation failed: {str(e)}"
            )

    def _validate_parameter(
        self,
        param: str,
        value: Any,
        rules: Dict[str, Any]
    ) -> List[str]:
        """Validate process parameter.
        
        Args:
            param: Parameter name
            value: Parameter value
            rules: Validation rules for parameter
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            # Check numeric range if specified
            if "range" in rules:
                error = check_numeric_range(
                    value,
                    min_val=rules["range"].get("min"),
                    max_val=rules["range"].get("max"),
                    field_name=param
                )
                if error:
                    errors.append(f"{param}: {rules['message']}")

            # Check enum values if specified
            if "values" in rules:
                error = check_enum_value(
                    value,
                    rules["values"],
                    field_name=param
                )
                if error:
                    errors.append(f"{param}: {rules['message']}")

        except Exception as e:
            errors.append(f"{param} validation error: {str(e)}")
        return errors

    def _validate_sequence(
        self,
        seq: str,
        data: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> List[str]:
        """Validate process sequence.
        
        Args:
            seq: Sequence name
            data: Sequence configuration data
            rules: Validation rules for sequence
            
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
                    f"{seq}: {rules['required_fields']['message']}"
                ))

            # Check unknown fields
            if "optional_fields" in rules:
                errors.extend(check_unknown_fields(
                    data,
                    rules["required_fields"]["fields"] + rules["optional_fields"]["fields"],
                    f"{seq}: {rules['optional_fields']['message']}"
                ))

            # Validate steps if present
            if "steps" in rules and "steps" in data:
                for step in data["steps"]:
                    step_errors = self._validate_step(
                        seq,
                        step,
                        rules["steps"]
                    )
                    errors.extend(step_errors)

        except Exception as e:
            errors.append(f"{seq} validation error: {str(e)}")
        return errors

    def _validate_step(
        self,
        seq: str,
        step: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> List[str]:
        """Validate sequence step.
        
        Args:
            seq: Sequence name
            step: Step configuration data
            rules: Validation rules for steps
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            # Check required fields
            if "required_fields" in rules:
                errors.extend(check_required_fields(
                    step,
                    rules["required_fields"]["fields"],
                    f"{seq} step: {rules['required_fields']['message']}"
                ))

            # Check unknown fields
            if "optional_fields" in rules:
                errors.extend(check_unknown_fields(
                    step,
                    rules["required_fields"]["fields"] + rules["optional_fields"]["fields"],
                    f"{seq} step: {rules['optional_fields']['message']}"
                ))

            # Validate step type
            if "type" in step:
                error = check_enum_value(
                    step["type"],
                    rules["types"]["values"],
                    field_name=f"{seq} step type"
                )
                if error:
                    errors.append(f"{seq} step: {rules['types']['message']}")

            # Validate step parameters
            if "parameters" in rules and "parameters" in step:
                for param, param_rules in rules["parameters"].items():
                    if param in step["parameters"]:
                        error = check_numeric_range(
                            step["parameters"][param],
                            min_val=param_rules.get("min"),
                            max_val=param_rules.get("max"),
                            field_name=f"{seq} step {param}"
                        )
                        if error:
                            errors.append(f"{seq} step: {param_rules['message']}")

        except Exception as e:
            errors.append(f"{seq} step validation error: {str(e)}")
        return errors
