"""Hardware validator."""

from typing import Dict, Any, List
from dataclasses import dataclass

from ...messaging import MessagingService
from ..exceptions import ValidationError
from .base import BaseValidator


@dataclass
class HardwareState:
    """Hardware state data."""
    chamber_pressure: float = 0.0
    main_pressure: float = 0.0
    regulator_pressure: float = 0.0
    z_position: float = 0.0
    safe_z_height: float = 0.0
    main_flow: float = 0.0
    feeder_flow: float = 0.0
    main_flow_setpoint: float = 0.0
    feeder_flow_setpoint: float = 0.0


class HardwareValidator(BaseValidator):
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
        super().__init__(validation_rules, message_broker)

    async def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate hardware conditions.
        
        Args:
            data: Hardware data to validate
            
        Returns:
            Dict containing validation results
            
        Raises:
            ValidationError: If validation fails
        """
        errors = []
        warnings = []
        
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
            raise ValidationError("Hardware validation failed", {"error": str(e)})

    async def _get_hardware_state(self) -> HardwareState:
        """Get current hardware state.
        
        Returns:
            Current hardware state
            
        Raises:
            ValidationError: If state cannot be retrieved
        """
        try:
            return HardwareState(
                chamber_pressure=await self._get_tag_value("pressure.chamber_pressure"),
                main_pressure=await self._get_tag_value("pressure.main_supply_pressure"),
                regulator_pressure=await self._get_tag_value("pressure.regulator_pressure"),
                z_position=await self._get_tag_value("motion.position.z_position"),
                safe_z_height=await self._get_tag_value("safety.safe_z"),
                main_flow=await self._get_tag_value("gas_control.main_flow.measured"),
                feeder_flow=await self._get_tag_value("gas_control.feeder_flow.measured"),
                main_flow_setpoint=await self._get_tag_value("gas_control.main_flow.setpoint"),
                feeder_flow_setpoint=await self._get_tag_value("gas_control.feeder_flow.setpoint")
            )
        except Exception as e:
            raise ValidationError("Failed to get hardware state", {"error": str(e)})

    async def _validate_chamber_pressure(self, state: HardwareState) -> List[str]:
        """Validate chamber pressure.
        
        Args:
            state: Current hardware state
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["states"]["chamber_vacuum"]["checks"][0]
            
            if state.chamber_pressure > rules["value"]:
                errors.append(rules["message"])
                
        except Exception as e:
            errors.append(f"Chamber pressure validation error: {str(e)}")
        return errors

    async def _validate_gas_pressures(self, state: HardwareState) -> List[str]:
        """Validate gas pressures.
        
        Args:
            state: Current hardware state
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["validation"]["gas_pressure"]
            
            if state.main_pressure < state.regulator_pressure + rules["min_margin"]:
                errors.append(rules["message"])
                
        except Exception as e:
            errors.append(f"Gas pressure validation error: {str(e)}")
        return errors

    async def _validate_position(self, state: HardwareState) -> List[str]:
        """Validate position.
        
        Args:
            state: Current hardware state
            
        Returns:
            List of error messages
        """
        errors = []
        try:
            rules = self._rules["sequences"]["safe_position"]
            
            if state.z_position < state.safe_z_height:
                errors.append(rules["message"])
                
        except Exception as e:
            errors.append(f"Position validation error: {str(e)}")
        return errors

    async def _validate_flow_stability(self, state: HardwareState) -> List[str]:
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
            main_error = abs(state.main_flow - state.main_flow_setpoint)
            if main_error > rules["main_tolerance"]:
                errors.append(rules["main_flow"]["message"])
                
            # Check feeder flow stability
            feeder_error = abs(state.feeder_flow - state.feeder_flow_setpoint)
            if feeder_error > rules["feeder_tolerance"]:
                errors.append(rules["feeder_flow"]["message"])
                
        except Exception as e:
            errors.append(f"Flow stability validation error: {str(e)}")
        return errors
