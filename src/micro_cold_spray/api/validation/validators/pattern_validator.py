"""Pattern validator."""

from typing import Dict, Any, List, Optional
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.validation.validators.base_validator import (
    check_required_fields,
    check_unknown_fields,
    check_numeric_range,
    check_enum_value,
    check_pattern
)


class PatternValidator:
    """Validator for spray patterns."""

    def __init__(
        self,
        validation_rules: Dict[str, Any],
        message_broker: Optional[MessagingService] = None
    ):
        """Initialize pattern validator.
        
        Args:
            validation_rules: Validation rules from config
            message_broker: Optional message broker for hardware checks
        """
        self._rules = validation_rules
        self._message_broker = message_broker

    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern data.
        
        Args:
            data: Pattern data to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        try:
            # Check required fields
            if "patterns" not in self._rules:
                raise ValueError("No pattern validation rules found")
                
            pattern_rules = self._rules["patterns"]
            
            # Check pattern type
            pattern_type = data.get("type")
            if not pattern_type:
                errors.append("Missing pattern type")
            elif pattern_type not in pattern_rules:
                errors.append(f"Unknown pattern type: {pattern_type}")
            else:
                # Validate based on pattern type
                if pattern_type == "serpentine":
                    type_errors = await self._validate_serpentine_pattern(data)
                    errors.extend(type_errors)
                elif pattern_type == "spiral":
                    type_errors = await self._validate_spiral_pattern(data)
                    errors.extend(type_errors)
                else:
                    errors.append(f"Validation not implemented for pattern type: {pattern_type}")

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

    async def _validate_serpentine_pattern(self, data: Dict[str, Any]) -> List[str]:
        """Validate serpentine pattern parameters.
        
        Args:
            data: Pattern data
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["patterns"]["serpentine"]
            params = data.get("params", {})
            
            # Check required parameters
            errors.extend(check_required_fields(
                params,
                rules["required_fields"]["fields"],
                "Serpentine pattern: "
            ))
            
            # Check for unknown parameters
            if "optional_fields" in rules:
                valid_fields = (
                    rules["required_fields"]["fields"] +
                    rules["optional_fields"]["fields"]
                )
                errors.extend(check_unknown_fields(
                    params,
                    valid_fields,
                    "Serpentine pattern: "
                ))
            
            # Validate parameter values
            if "length" in params:
                error = check_numeric_range(
                    params["length"],
                    min_val=0,
                    field_name="Length"
                )
                if error:
                    errors.append(f"Serpentine pattern: {error}")
                    
            if "spacing" in params:
                error = check_numeric_range(
                    params["spacing"],
                    min_val=0,
                    field_name="Spacing"
                )
                if error:
                    errors.append(f"Serpentine pattern: {error}")
                    
            if "direction" in params:
                error = check_enum_value(
                    params["direction"],
                    ["x", "y"],
                    field_name="Direction"
                )
                if error:
                    errors.append(f"Serpentine pattern: {error}")
                    
        except Exception as e:
            errors.append(f"Serpentine pattern validation error: {str(e)}")
        return errors

    async def _validate_spiral_pattern(self, data: Dict[str, Any]) -> List[str]:
        """Validate spiral pattern parameters.
        
        Args:
            data: Pattern data
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["patterns"]["spiral"]
            params = data.get("params", {})
            
            # Check required parameters
            errors.extend(check_required_fields(
                params,
                rules["required_fields"]["fields"],
                "Spiral pattern: "
            ))
            
            # Check for unknown parameters
            if "optional_fields" in rules:
                valid_fields = (
                    rules["required_fields"]["fields"] +
                    rules["optional_fields"]["fields"]
                )
                errors.extend(check_unknown_fields(
                    params,
                    valid_fields,
                    "Spiral pattern: "
                ))
            
            # Validate parameter values
            if "radius" in params:
                error = check_numeric_range(
                    params["radius"],
                    min_val=0,
                    field_name="Radius"
                )
                if error:
                    errors.append(f"Spiral pattern: {error}")
                    
            if "spacing" in params:
                error = check_numeric_range(
                    params["spacing"],
                    min_val=0,
                    field_name="Spacing"
                )
                if error:
                    errors.append(f"Spiral pattern: {error}")
                    
            if "direction" in params:
                error = check_enum_value(
                    params["direction"],
                    ["CW", "CCW"],
                    field_name="Direction"
                )
                if error:
                    errors.append(f"Spiral pattern: {error}")
                    
        except Exception as e:
            errors.append(f"Spiral pattern validation error: {str(e)}")
        return errors
