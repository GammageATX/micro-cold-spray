"""Parameter validator."""

from typing import Dict, Any, List
from fastapi import status, HTTPException

from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.validation.validators.base_validator import BaseValidator


class ParameterValidator(BaseValidator):
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
        super().__init__(validation_rules, message_broker)

    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate process parameters.
        
        Args:
            data: Parameter data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            HTTPException: If validation fails
        """
        errors = []
        warnings = []
        
        try:
            # Check required fields
            required = self._rules["parameters"]["required_fields"]
            errors.extend(self._check_required_fields(
                data,
                required["fields"],
                "Parameters: "
            ))

            # Validate gas settings
            if "gas_flows" in data:
                gas_errors = await self._validate_gas_parameters(data["gas_flows"])
                errors.extend(gas_errors)

            # Validate powder feed settings
            if "powder_feed" in data:
                feed_errors = await self._validate_powder_feed(data["powder_feed"])
                errors.extend(feed_errors)

            # Validate material settings
            if "material" in data:
                material_errors = await self._validate_material(data["material"])
                errors.extend(material_errors)

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
                message="Parameter validation failed",
                context={"error": str(e)},
                cause=e
            )

    async def _validate_gas_parameters(self, gas_data: Dict[str, Any]) -> List[str]:
        """Validate gas flow parameters.
        
        Args:
            gas_data: Gas flow data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["parameters"]["gas_flows"]
            
            # Check required gas flow fields
            required_fields = ["gas_type", "main_gas", "feeder_gas"]
            errors.extend(self._check_required_fields(
                gas_data,
                required_fields,
                "Gas flows: "
            ))
            
            # Validate gas type if present
            if "gas_type" in gas_data:
                error = self._check_enum_value(
                    gas_data["gas_type"],
                    rules["gas_type"]["choices"],
                    "Gas type"
                )
                if error:
                    errors.append(error)
                
            # Validate flow rates if present
            if "main_gas" in gas_data:
                error = self._check_numeric_range(
                    gas_data["main_gas"],
                    rules["main_gas"]["min"],
                    rules["main_gas"]["max"],
                    "Main gas flow"
                )
                if error:
                    errors.append(error)
                    
            if "feeder_gas" in gas_data:
                error = self._check_numeric_range(
                    gas_data["feeder_gas"],
                    rules["feeder_gas"]["min"],
                    rules["feeder_gas"]["max"],
                    "Feeder gas flow"
                )
                if error:
                    errors.append(error)
                    
        except Exception as e:
            errors.append(f"Gas parameter validation error: {str(e)}")
        return errors

    async def _validate_powder_feed(self, feed_data: Dict[str, Any]) -> List[str]:
        """Validate powder feed parameters.
        
        Args:
            feed_data: Powder feed data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["parameters"]["powder_feed"]
            
            # Check required powder feed fields
            required_fields = ["frequency", "deagglomerator"]
            errors.extend(self._check_required_fields(
                feed_data,
                required_fields,
                "Powder feed: "
            ))
            
            # Validate frequency if present
            if "frequency" in feed_data:
                error = self._check_numeric_range(
                    feed_data["frequency"],
                    rules["frequency"]["min"],
                    rules["frequency"]["max"],
                    "Feed frequency"
                )
                if error:
                    errors.append(error)
                    
            # Validate deagglomerator if present
            if "deagglomerator" in feed_data:
                deagg = feed_data["deagglomerator"]
                if not isinstance(deagg, dict):
                    errors.append("Deagglomerator settings must be an object")
                else:
                    if "speed" not in deagg:
                        errors.append("Deagglomerator speed not specified")
                    else:
                        error = self._check_enum_value(
                            deagg["speed"],
                            rules["deagglomerator"]["speed"]["choices"],
                            "Deagglomerator speed"
                        )
                        if error:
                            errors.append(error)
                    
        except Exception as e:
            errors.append(f"Powder feed validation error: {str(e)}")
        return errors

    async def _validate_material(self, material_data: Dict[str, Any]) -> List[str]:
        """Validate material parameters.
        
        Args:
            material_data: Material data to validate
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["parameters"]["material"]
            
            # Check required fields
            if "required_fields" in rules:
                errors.extend(self._check_required_fields(
                    material_data,
                    rules["required_fields"]["fields"],
                    "Material: "
                ))
                
            # Check for unknown fields
            if "optional_fields" in rules:
                valid_fields = (
                    rules["required_fields"]["fields"] +
                    rules["optional_fields"]["fields"]
                )
                errors.extend(self._check_unknown_fields(
                    material_data,
                    valid_fields,
                    "Material: "
                ))
                
            # Validate material type if present
            if "type" in material_data:
                error = self._check_enum_value(
                    material_data["type"],
                    rules["type"]["choices"],
                    "Material type"
                )
                if error:
                    errors.append(error)
                    
            # Validate particle size if present
            if "particle_size" in material_data:
                size = material_data["particle_size"]
                error = self._check_numeric_range(
                    size,
                    rules["particle_size"]["min"],
                    rules["particle_size"]["max"],
                    "Particle size"
                )
                if error:
                    errors.append(error)
                    
        except Exception as e:
            errors.append(f"Material validation error: {str(e)}")
        return errors
