"""Parameter validator."""

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
    check_pattern
)


class ParameterValidator:
    """Validator for process parameters."""

    def __init__(
        self,
        validation_rules: Dict[str, Any],
        message_broker: MessagingService
    ):
        """Initialize parameter validator.
        
        Args:
            validation_rules: Validation rules from config
            message_broker: Message broker for hardware checks
        """
        self._rules = validation_rules
        self._message_broker = message_broker

    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameter data.
        
        Args:
            data: Parameter data to validate
            
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
            if "parameters" not in self._rules:
                raise ValueError("No parameter validation rules found")
                
            param_rules = self._rules["parameters"]
            
            # Check parameter type
            param_type = data.get("type")
            if not param_type:
                errors.append("Missing parameter type")
            elif param_type not in param_rules:
                errors.append(f"Unknown parameter type: {param_type}")
            else:
                # Validate based on parameter type
                if param_type == "gas":
                    type_errors = await self._validate_gas_parameters(data)
                    errors.extend(type_errors)
                elif param_type == "powder":
                    type_errors = await self._validate_powder_parameters(data)
                    errors.extend(type_errors)
                elif param_type == "material":
                    type_errors = await self._validate_material_parameters(data)
                    errors.extend(type_errors)
                else:
                    errors.append(f"Validation not implemented for parameter type: {param_type}")

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

    async def _validate_gas_parameters(self, data: Dict[str, Any]) -> List[str]:
        """Validate gas parameters.
        
        Args:
            data: Gas parameter data
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["parameters"]["gas"]
            params = data.get("params", {})
            
            # Check required parameters
            errors.extend(check_required_fields(
                params,
                rules["required_fields"]["fields"],
                "Gas parameters: "
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
                    "Gas parameters: "
                ))
            
            # Validate parameter values
            if "flow_rate" in params:
                error = check_numeric_range(
                    params["flow_rate"],
                    min_val=rules["flow_rate"]["min"],
                    max_val=rules["flow_rate"]["max"],
                    field_name="Flow rate"
                )
                if error:
                    errors.append(f"Gas parameters: {error}")
                    
            if "pressure" in params:
                error = check_numeric_range(
                    params["pressure"],
                    min_val=rules["pressure"]["min"],
                    max_val=rules["pressure"]["max"],
                    field_name="Pressure"
                )
                if error:
                    errors.append(f"Gas parameters: {error}")
                    
            if "type" in params:
                error = check_enum_value(
                    params["type"],
                    rules["type"]["values"],
                    field_name="Gas type"
                )
                if error:
                    errors.append(f"Gas parameters: {error}")
                    
        except Exception as e:
            errors.append(f"Gas parameter validation error: {str(e)}")
        return errors

    async def _validate_powder_parameters(self, data: Dict[str, Any]) -> List[str]:
        """Validate powder parameters.
        
        Args:
            data: Powder parameter data
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["parameters"]["powder"]
            params = data.get("params", {})
            
            # Check required parameters
            errors.extend(check_required_fields(
                params,
                rules["required_fields"]["fields"],
                "Powder parameters: "
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
                    "Powder parameters: "
                ))
            
            # Validate parameter values
            if "feed_rate" in params:
                error = check_numeric_range(
                    params["feed_rate"],
                    min_val=rules["feed_rate"]["min"],
                    max_val=rules["feed_rate"]["max"],
                    field_name="Feed rate"
                )
                if error:
                    errors.append(f"Powder parameters: {error}")
                    
            if "carrier_gas_flow" in params:
                error = check_numeric_range(
                    params["carrier_gas_flow"],
                    min_val=rules["carrier_gas_flow"]["min"],
                    max_val=rules["carrier_gas_flow"]["max"],
                    field_name="Carrier gas flow"
                )
                if error:
                    errors.append(f"Powder parameters: {error}")
                    
        except Exception as e:
            errors.append(f"Powder parameter validation error: {str(e)}")
        return errors

    async def _validate_material_parameters(self, data: Dict[str, Any]) -> List[str]:
        """Validate material parameters.
        
        Args:
            data: Material parameter data
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["parameters"]["material"]
            params = data.get("params", {})
            
            # Check required parameters
            errors.extend(check_required_fields(
                params,
                rules["required_fields"]["fields"],
                "Material parameters: "
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
                    "Material parameters: "
                ))
            
            # Validate parameter values
            if "type" in params:
                error = check_enum_value(
                    params["type"],
                    rules["type"]["values"],
                    field_name="Material type"
                )
                if error:
                    errors.append(f"Material parameters: {error}")
                    
            if "particle_size" in params:
                error = check_numeric_range(
                    params["particle_size"],
                    min_val=rules["particle_size"]["min"],
                    max_val=rules["particle_size"]["max"],
                    field_name="Particle size"
                )
                if error:
                    errors.append(f"Material parameters: {error}")
                    
            if "lot_number" in params:
                error = check_pattern(
                    params["lot_number"],
                    rules["lot_number"]["pattern"],
                    field_name="Lot number"
                )
                if error:
                    errors.append(f"Material parameters: {error}")
                    
        except Exception as e:
            errors.append(f"Material parameter validation error: {str(e)}")
        return errors
