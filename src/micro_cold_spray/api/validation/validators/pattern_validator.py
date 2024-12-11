"""Pattern validator."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ...config import ConfigService
from ...messaging import MessagingService
from ..exceptions import ValidationError
from .base import BaseValidator


@dataclass
class PatternBounds:
    """Pattern bounds in 3D space."""
    min_x: float = 0.0
    max_x: float = 0.0
    min_y: float = 0.0
    max_y: float = 0.0
    min_z: float = 0.0
    max_z: float = 0.0


class PatternValidator(BaseValidator):
    """Validator for spray patterns."""

    def __init__(
        self,
        validation_rules: Dict[str, Any],
        config_service: ConfigService,
        message_broker: Optional[MessagingService] = None
    ):
        """Initialize pattern validator.
        
        Args:
            validation_rules: Validation rules from config
            config_service: Configuration service for hardware limits
            message_broker: Optional message broker for hardware checks
        """
        super().__init__(validation_rules, message_broker)
        self._config_service = config_service

    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pattern definition.
        
        Args:
            data: Pattern data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            ValidationError: If validation fails
        """
        errors = []
        warnings = []
        
        try:
            pattern_type = data.get("type")
            if not pattern_type:
                errors.append("Pattern type not specified")
                return {"valid": False, "errors": errors}

            # Get pattern validation rules
            rules = self._rules["patterns"]
            
            # Validate pattern bounds
            if "limits" in rules:
                bound_errors = await self._validate_pattern_bounds(
                    data,
                    rules["limits"]
                )
                errors.extend(bound_errors)

            # Validate type-specific parameters
            if pattern_type == "serpentine":
                type_errors = await self._validate_serpentine_pattern(data)
                errors.extend(type_errors)
            elif pattern_type == "spiral":
                type_errors = await self._validate_spiral_pattern(data)
                errors.extend(type_errors)
            else:
                errors.append(f"Unknown pattern type: {pattern_type}")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            raise ValidationError("Pattern validation failed", {"error": str(e)})

    async def _validate_pattern_bounds(
        self,
        pattern: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> List[str]:
        """Validate pattern bounds against stage limits.
        
        Args:
            pattern: Pattern data
            rules: Validation rules for bounds
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            # Get stage dimensions from hardware config
            hw_config = await self._config_service.get_config("hardware")
            stage = hw_config["hardware"]["physical"]["stage"]["dimensions"]
            
            # Calculate pattern bounds
            bounds = await self._calculate_pattern_bounds(pattern)
            
            # Check X limits
            if bounds.min_x < 0 or bounds.max_x > stage["x"]:
                errors.append(rules["position"]["message"])
                
            # Check Y limits
            if bounds.min_y < 0 or bounds.max_y > stage["y"]:
                errors.append(rules["position"]["message"])
                
            # Check Z limits
            if bounds.min_z < 0 or bounds.max_z > stage["z"]:
                errors.append(rules["position"]["message"])
                
            # Check speed limits if specified
            if "speed" in pattern:
                speed = pattern["speed"]
                if speed > hw_config["hardware"]["safety"]["motion"]["max_speed"]:
                    errors.append(rules["speed"]["message"])
                    
        except Exception as e:
            errors.append(f"Pattern bounds validation error: {str(e)}")
        return errors

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
            errors.extend(self._check_required_fields(
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
                errors.extend(self._check_unknown_fields(
                    params,
                    valid_fields,
                    "Serpentine pattern: "
                ))
            
            # Validate parameter values
            if "length" in params:
                error = self._check_numeric_range(
                    params["length"],
                    min_val=0,
                    field_name="Length"
                )
                if error:
                    errors.append(f"Serpentine pattern: {error}")
                    
            if "spacing" in params:
                error = self._check_numeric_range(
                    params["spacing"],
                    min_val=0,
                    field_name="Spacing"
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
            errors.extend(self._check_required_fields(
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
                errors.extend(self._check_unknown_fields(
                    params,
                    valid_fields,
                    "Spiral pattern: "
                ))
            
            # Validate parameter values
            if "diameter" in params:
                error = self._check_numeric_range(
                    params["diameter"],
                    min_val=0,
                    field_name="Diameter"
                )
                if error:
                    errors.append(f"Spiral pattern: {error}")
                    
            if "pitch" in params:
                error = self._check_numeric_range(
                    params["pitch"],
                    min_val=0,
                    field_name="Pitch"
                )
                if error:
                    errors.append(f"Spiral pattern: {error}")
                    
        except Exception as e:
            errors.append(f"Spiral pattern validation error: {str(e)}")
        return errors

    async def _calculate_pattern_bounds(self, pattern: Dict[str, Any]) -> PatternBounds:
        """Calculate pattern bounds based on type.
        
        Args:
            pattern: Pattern data
            
        Returns:
            Pattern bounds
        """
        pattern_type = pattern.get("type")
        params = pattern.get("params", {})
        
        if pattern_type == "serpentine":
            return PatternBounds(
                max_x=params.get("length", 0),
                max_y=params.get("width", 0)
            )
        elif pattern_type == "spiral":
            diameter = params.get("diameter", 0)
            radius = diameter / 2
            return PatternBounds(
                min_x=-radius,
                max_x=radius,
                min_y=-radius,
                max_y=radius
            )
            
        return PatternBounds()
