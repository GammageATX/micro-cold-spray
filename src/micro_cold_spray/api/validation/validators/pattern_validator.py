"""Pattern validator."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from fastapi import status, HTTPException

from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.validation.validators.base_validator import BaseValidator


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
            HTTPException: If validation fails
        """
        errors = []
        warnings = []
        
        try:
            pattern_type = data.get("type")
            if not pattern_type:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Pattern type not specified"
                )

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
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Unknown pattern type",
                    context={"type": pattern_type}
                )

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }

        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Pattern validation failed",
                context={"error": str(e)},
                cause=e
            )

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
            
        Raises:
            HTTPException: If hardware config cannot be retrieved
        """
        errors = []
        try:
            # Get stage dimensions from hardware config
            hw_config = await self._config_service.get_config("hardware")
            if not hw_config or not hw_config.data:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Hardware configuration not found"
                )
                
            stage = hw_config.data["hardware"]["physical"]["stage"]["dimensions"]
            
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
                if speed > hw_config.data["hardware"]["safety"]["motion"]["max_speed"]:
                    errors.append(rules["speed"]["message"])
                    
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Pattern bounds validation failed",
                context={"error": str(e)},
                cause=e
            )
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
        """Calculate pattern bounds in 3D space.
        
        Args:
            pattern: Pattern data
            
        Returns:
            Pattern bounds
        """
        bounds = PatternBounds()
        
        # Get pattern position
        position = pattern.get("position", {})
        x = position.get("x", 0.0)
        y = position.get("y", 0.0)
        z = position.get("z", 0.0)
        
        # Calculate bounds based on pattern type
        pattern_type = pattern.get("type")
        params = pattern.get("params", {})
        
        if pattern_type == "serpentine":
            length = params.get("length", 0.0)
            spacing = params.get("spacing", 0.0)
            
            bounds.min_x = x
            bounds.max_x = x + length
            bounds.min_y = y
            bounds.max_y = y + spacing
            bounds.min_z = z
            bounds.max_z = z
            
        elif pattern_type == "spiral":
            diameter = params.get("diameter", 0.0)
            
            bounds.min_x = x - diameter / 2
            bounds.max_x = x + diameter / 2
            bounds.min_y = y - diameter / 2
            bounds.max_y = y + diameter / 2
            bounds.min_z = z
            bounds.max_z = z
            
        return bounds
