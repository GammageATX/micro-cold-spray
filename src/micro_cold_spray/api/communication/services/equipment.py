"""Equipment control service."""

from typing import Dict, Any
from loguru import logger

from ...base import ConfigurableService
from ...base.exceptions import HardwareError, ValidationError
from ..clients import PLCClient


class EquipmentService(ConfigurableService):
    """Service for controlling process equipment."""

    def __init__(self, plc_client: PLCClient):
        """Initialize equipment service.
        
        Args:
            plc_client: PLC client for hardware communication
        """
        super().__init__(service_name="equipment")
        self._plc = plc_client

    async def set_gas_flow(self, flow_type: str, value: float) -> None:
        """Set gas flow setpoint.
        
        Args:
            flow_type: Flow type (main or feeder)
            value: Flow setpoint in SLPM
            
        Raises:
            HardwareError: If setting flow fails
            ValidationError: If parameters invalid
        """
        if flow_type not in ['main', 'feeder']:
            raise ValidationError(f"Invalid flow type: {flow_type}")

        # Get tag based on type
        tag = "AOS32-0.1.2.1" if flow_type == "main" else "AOS32-0.1.2.2"
        
        # Get limits from tags.yaml
        limits = {
            'main': (0.0, 100.0),
            'feeder': (0.0, 10.0)
        }[flow_type]
        
        if not limits[0] <= value <= limits[1]:
            raise ValidationError(
                f"{flow_type} flow must be between {limits[0]} and {limits[1]} SLPM",
                {"flow_type": flow_type, "value": value, "limits": limits}
            )
            
        try:
            await self._plc.write_tag(tag, value)
            logger.info(f"Set {flow_type} gas flow to {value} SLPM")
        except Exception as e:
            raise HardwareError(
                f"Failed to set {flow_type} gas flow",
                "gas_control",
                {
                    "type": flow_type,
                    "value": value,
                    "error": str(e)
                }
            )

    async def set_gas_valve(self, valve: str, state: bool) -> None:
        """Control gas valve.
        
        Args:
            valve: Valve to control (main, feeder)
            state: Valve state (True=open, False=closed)
            
        Raises:
            HardwareError: If valve control fails
            ValidationError: If valve invalid
        """
        if valve not in ['main', 'feeder']:
            raise ValidationError(f"Invalid valve: {valve}")
            
        try:
            tag = "MainSwitch" if valve == "main" else "FeederSwitch"
            await self._plc.write_tag(tag, state)
            state_str = "opened" if state else "closed"
            logger.info(f"{valve.title()} gas valve {state_str}")
        except Exception as e:
            raise HardwareError(
                f"Failed to control {valve} gas valve",
                "gas_control",
                {
                    "valve": valve,
                    "state": state,
                    "error": str(e)
                }
            )

    async def control_vacuum_pump(self, pump: str, state: bool) -> None:
        """Control vacuum pump.
        
        Args:
            pump: Pump to control (mechanical, booster)
            state: Pump state (True=start, False=stop)
            
        Raises:
            HardwareError: If pump control fails
            ValidationError: If pump invalid
        """
        if pump not in ['mechanical', 'booster']:
            raise ValidationError(f"Invalid pump: {pump}")
            
        try:
            if pump == 'mechanical':
                tag = "MechPumpStart" if state else "MechPumpStop"
            else:
                tag = "BoosterPumpStart" if state else "BoosterPumpStop"
                
            await self._plc.write_tag(tag, True)  # Pulse the start/stop tag
            pump_state = "started" if state else "stopped"
            logger.info(f"{pump.title()} pump {pump_state}")
        except Exception as e:
            raise HardwareError(
                f"Failed to control {pump} pump",
                "vacuum",
                {
                    "pump": pump,
                    "state": state,
                    "error": str(e)
                }
            )

    async def control_shutter(self, state: bool) -> None:
        """Control nozzle shutter.
        
        Args:
            state: Shutter state (True=open, False=closed)
            
        Raises:
            HardwareError: If shutter control fails
        """
        try:
            await self._plc.write_tag("Shutter", state)
            state_str = "opened" if state else "closed"
            logger.info(f"Nozzle shutter {state_str}")
        except Exception as e:
            raise HardwareError(
                "Failed to control nozzle shutter",
                "nozzle",
                {
                    "state": state,
                    "error": str(e)
                }
            )

    async def control_gate_valve(self, position: str) -> None:
        """Control vacuum gate valve.
        
        Args:
            position: Gate valve position (open, partial, closed)
            
        Raises:
            HardwareError: If gate valve control fails
            ValidationError: If position invalid
        """
        if position not in ['open', 'partial', 'closed']:
            raise ValidationError(f"Invalid gate valve position: {position}")
            
        try:
            if position == 'open':
                await self._plc.write_tag("Open", True)
                await self._plc.write_tag("Partial", False)
            elif position == 'partial':
                await self._plc.write_tag("Open", False)
                await self._plc.write_tag("Partial", True)
            else:  # closed
                await self._plc.write_tag("Open", False)
                await self._plc.write_tag("Partial", False)
                
            logger.info(f"Gate valve moved to {position}")
        except Exception as e:
            raise HardwareError(
                "Failed to control gate valve",
                "vacuum",
                {
                    "position": position,
                    "error": str(e)
                }
            )

    async def get_status(self) -> Dict[str, Any]:
        """Get equipment status.
        
        Returns:
            Dictionary with equipment status
            
        Raises:
            HardwareError: If reading status fails
        """
        try:
            status = {
                'gas': {
                    'main': {
                        'flow': await self._plc.read_tag("MainFlowRate"),
                        'setpoint': await self._plc.read_tag("AOS32-0.1.2.1"),
                        'valve': await self._plc.read_tag("MainSwitch")
                    },
                    'feeder': {
                        'flow': await self._plc.read_tag("FeederFlowRate"),
                        'setpoint': await self._plc.read_tag("AOS32-0.1.2.2"),
                        'valve': await self._plc.read_tag("FeederSwitch")
                    }
                },
                'pressure': {
                    'main': await self._plc.read_tag("MainGasPressure"),
                    'feeder': await self._plc.read_tag("FeederPressure"),
                    'nozzle': await self._plc.read_tag("NozzlePressure"),
                    'regulator': await self._plc.read_tag("RegulatorPressure"),
                    'chamber': await self._plc.read_tag("ChamberPressure")
                },
                'vacuum': {
                    'gate_valve': {
                        'open': await self._plc.read_tag("Open"),
                        'partial': await self._plc.read_tag("Partial")
                    },
                    'shutter': await self._plc.read_tag("Shutter")
                }
            }
            return status
            
        except Exception as e:
            raise HardwareError(
                "Failed to get equipment status",
                "equipment",
                {"error": str(e)}
            )
