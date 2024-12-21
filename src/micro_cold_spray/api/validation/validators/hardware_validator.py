"""Hardware validator."""

from typing import Dict, Any, List
from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.validation.validators.base_validator import (
    get_tag_value,
    check_numeric_range
)


class HardwareValidator:
    """Validator for hardware conditions."""

    def __init__(
        self,
        validation_rules: Dict[str, Any],
        message_broker: MessagingService
    ):
        """Initialize hardware validator.
        
        Args:
            validation_rules: Validation rules from config
            message_broker: Message broker for hardware checks
        """
        self._rules = validation_rules
        self._message_broker = message_broker

    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hardware conditions.
        
        Args:
            data: Hardware data to validate
            
        Returns:
            Dict containing:
                - valid: Whether validation passed
                - errors: List of error messages
                - warnings: List of warning messages
        """
        errors: List[str] = []
        warnings: List[str] = []
        
        try:
            # Get current hardware state
            state = await self._get_hardware_state()
            
            # Validate chamber pressure
            pressure_errors = await self._validate_chamber_pressure(state)
            errors.extend(pressure_errors)
            
            # Validate gas pressures
            gas_errors = await self._validate_gas_pressures(state)
            errors.extend(gas_errors)
            
            # Validate position
            position_errors = await self._validate_position(state)
            errors.extend(position_errors)
            
            # Validate flow stability
            flow_errors = await self._validate_flow_stability(state)
            errors.extend(flow_errors)

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

    async def _get_hardware_state(self) -> Dict[str, Any]:
        """Get current hardware state.
        
        Returns:
            Hardware state data
            
        Raises:
            HTTPException: If state cannot be retrieved
        """
        try:
            # Get chamber pressure
            chamber_pressure = await get_tag_value(
                self._message_broker,
                "chamber_pressure"
            )
            
            # Get gas pressures
            main_pressure = await get_tag_value(
                self._message_broker,
                "main_pressure"
            )
            regulator_pressure = await get_tag_value(
                self._message_broker,
                "regulator_pressure"
            )
            
            # Get position
            z_position = await get_tag_value(
                self._message_broker,
                "z_position"
            )
            safe_z_height = await get_tag_value(
                self._message_broker,
                "safe_z_height"
            )
            
            # Get flow rates
            main_flow = await get_tag_value(
                self._message_broker,
                "main_flow"
            )
            main_flow_setpoint = await get_tag_value(
                self._message_broker,
                "main_flow_setpoint"
            )
            feeder_flow = await get_tag_value(
                self._message_broker,
                "feeder_flow"
            )
            feeder_flow_setpoint = await get_tag_value(
                self._message_broker,
                "feeder_flow_setpoint"
            )
            
            return {
                "chamber_pressure": chamber_pressure,
                "main_pressure": main_pressure,
                "regulator_pressure": regulator_pressure,
                "z_position": z_position,
                "safe_z_height": safe_z_height,
                "main_flow": main_flow,
                "main_flow_setpoint": main_flow_setpoint,
                "feeder_flow": feeder_flow,
                "feeder_flow_setpoint": feeder_flow_setpoint
            }
            
        except Exception as e:
            logger.error(f"Failed to get hardware state: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to get hardware state: {str(e)}"
            )

    async def _validate_chamber_pressure(self, state: Dict[str, Any]) -> List[str]:
        """Validate chamber pressure.
        
        Args:
            state: Current hardware state
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["states"]["chamber_vacuum"]["checks"][0]
            
            error = check_numeric_range(
                state["chamber_pressure"],
                max_val=rules["value"],
                field_name="Chamber pressure"
            )
            if error:
                errors.append(rules["message"])
                
        except Exception as e:
            errors.append(f"Chamber pressure validation error: {str(e)}")
        return errors

    async def _validate_gas_pressures(self, state: Dict[str, Any]) -> List[str]:
        """Validate gas pressures.
        
        Args:
            state: Current hardware state
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["validation"]["gas_pressure"]
            
            # Check main pressure is sufficiently above regulator pressure
            margin = state["main_pressure"] - state["regulator_pressure"]
            error = check_numeric_range(
                margin,
                min_val=rules["min_margin"],
                field_name="Gas pressure margin"
            )
            if error:
                errors.append(rules["message"])
                
        except Exception as e:
            errors.append(f"Gas pressure validation error: {str(e)}")
        return errors

    async def _validate_position(self, state: Dict[str, Any]) -> List[str]:
        """Validate position.
        
        Args:
            state: Current hardware state
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["sequences"]["safe_position"]
            
            # Check Z position is above safe height
            error = check_numeric_range(
                state["z_position"],
                min_val=state["safe_z_height"],
                field_name="Z position"
            )
            if error:
                errors.append(rules["message"])
                
        except Exception as e:
            errors.append(f"Position validation error: {str(e)}")
        return errors

    async def _validate_flow_stability(self, state: Dict[str, Any]) -> List[str]:
        """Validate gas flow stability.
        
        Args:
            state: Current hardware state
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["validation"]["flow_stability"]
            
            # Check main flow stability
            main_error = abs(state["main_flow"] - state["main_flow_setpoint"])
            error = check_numeric_range(
                main_error,
                max_val=rules["main_tolerance"],
                field_name="Main flow error"
            )
            if error:
                errors.append(rules["main_flow"]["message"])
                
            # Check feeder flow stability
            feeder_error = abs(state["feeder_flow"] - state["feeder_flow_setpoint"])
            error = check_numeric_range(
                feeder_error,
                max_val=rules["feeder_tolerance"],
                field_name="Feeder flow error"
            )
            if error:
                errors.append(rules["feeder_flow"]["message"])
                
        except Exception as e:
            errors.append(f"Flow stability validation error: {str(e)}")
        return errors
