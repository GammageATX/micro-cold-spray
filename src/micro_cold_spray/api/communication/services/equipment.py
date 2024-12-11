"""Equipment control service."""

from typing import Dict, Any
from loguru import logger

from ...base import BaseService
from ..exceptions import HardwareError
from ..clients import PLCClient
from ..models.equipment import (
    GasFlowRequest,
    GasValveRequest,
    PumpRequest,
    VacuumValveRequest,
    NozzleRequest,
    ShutterRequest
)


class EquipmentService(BaseService):
    """Service for controlling process equipment."""

    def __init__(self, plc_client: PLCClient):
        """Initialize equipment service.
        
        Args:
            plc_client: PLC client for hardware communication
        """
        super().__init__(service_name="equipment")
        self._plc = plc_client

    async def set_gas_flow(self, request: GasFlowRequest) -> None:
        """Set gas flow setpoint.
        
        Args:
            request: Gas flow request
            
        Raises:
            HardwareError: If setting flow fails
        """
        try:
            tag = f"gas.{request.type}.flow.setpoint"
            await self._plc.write_tag(tag, request.value)
            logger.info(f"Set {request.type} gas flow to {request.value} SLPM")
        except Exception as e:
            raise HardwareError(
                f"Failed to set {request.type} gas flow",
                "gas_control",
                {
                    "type": request.type,
                    "value": request.value,
                    "error": str(e)
                }
            )

    async def set_gas_valve(self, request: GasValveRequest) -> None:
        """Control gas valve.
        
        Args:
            request: Valve control request
            
        Raises:
            HardwareError: If valve control fails
        """
        try:
            tag = f"gas.{request.valve}.valve"
            await self._plc.write_tag(tag, request.state)
            state = "opened" if request.state else "closed"
            logger.info(f"{request.valve.title()} gas valve {state}")
        except Exception as e:
            raise HardwareError(
                f"Failed to control {request.valve} gas valve",
                "gas_control",
                {
                    "valve": request.valve,
                    "state": request.state,
                    "error": str(e)
                }
            )

    async def control_pump(self, request: PumpRequest) -> None:
        """Control vacuum pump.
        
        Args:
            request: Pump control request
            
        Raises:
            HardwareError: If pump control fails
        """
        try:
            await self._plc.write_tag("vacuum.pump", request.state)
            state = "started" if request.state else "stopped"
            logger.info(f"Vacuum pump {state}")
        except Exception as e:
            raise HardwareError(
                "Failed to control vacuum pump",
                "vacuum",
                {
                    "state": request.state,
                    "error": str(e)
                }
            )

    async def set_vacuum_valve(self, request: VacuumValveRequest) -> None:
        """Control vacuum valve.
        
        Args:
            request: Valve control request
            
        Raises:
            HardwareError: If valve control fails
        """
        try:
            tag = f"vacuum.{request.valve}"
            await self._plc.write_tag(tag, request.state)
            state = "opened" if request.state else "closed"
            logger.info(f"{request.valve.title()} vacuum valve {state}")
        except Exception as e:
            raise HardwareError(
                f"Failed to control {request.valve} vacuum valve",
                "vacuum",
                {
                    "valve": request.valve,
                    "state": request.state,
                    "error": str(e)
                }
            )

    async def control_nozzle(self, request: NozzleRequest) -> None:
        """Control nozzle heater.
        
        Args:
            request: Nozzle control request
            
        Raises:
            HardwareError: If heater control fails
        """
        try:
            await self._plc.write_tag("nozzle.heater", request.state)
            state = "enabled" if request.state else "disabled"
            logger.info(f"Nozzle heater {state}")
        except Exception as e:
            raise HardwareError(
                "Failed to control nozzle heater",
                "nozzle",
                {
                    "state": request.state,
                    "error": str(e)
                }
            )

    async def control_shutter(self, request: ShutterRequest) -> None:
        """Control nozzle shutter.
        
        Args:
            request: Shutter control request
            
        Raises:
            HardwareError: If shutter control fails
        """
        try:
            await self._plc.write_tag("nozzle.shutter", request.position)
            logger.info(f"Nozzle shutter moved to {request.position}")
        except Exception as e:
            raise HardwareError(
                "Failed to control nozzle shutter",
                "nozzle",
                {
                    "position": request.position,
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
            # Gas system status
            main_flow = await self._plc.read_tag("gas.main.flow.value")
            carrier_flow = await self._plc.read_tag("gas.carrier.flow.value")
            main_valve = await self._plc.read_tag("gas.main.valve")
            carrier_valve = await self._plc.read_tag("gas.carrier.valve")
            
            # Vacuum system status
            pump_state = await self._plc.read_tag("vacuum.pump")
            chamber_valve = await self._plc.read_tag("vacuum.chamber")
            bypass_valve = await self._plc.read_tag("vacuum.bypass")
            pressure = await self._plc.read_tag("vacuum.pressure")
            
            # Nozzle status
            heater_state = await self._plc.read_tag("nozzle.heater")
            temperature = await self._plc.read_tag("nozzle.temperature")
            shutter_pos = await self._plc.read_tag("nozzle.shutter")
            
            return {
                "gas": {
                    "main_flow": main_flow,
                    "carrier_flow": carrier_flow,
                    "main_valve": main_valve,
                    "carrier_valve": carrier_valve
                },
                "vacuum": {
                    "pump": pump_state,
                    "chamber_valve": chamber_valve,
                    "bypass_valve": bypass_valve,
                    "pressure": pressure
                },
                "nozzle": {
                    "heater": heater_state,
                    "temperature": temperature,
                    "shutter": shutter_pos
                }
            }
        except Exception as e:
            raise HardwareError(
                "Failed to get equipment status",
                "equipment",
                {"error": str(e)}
            )
