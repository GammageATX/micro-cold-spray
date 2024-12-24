"""Equipment service implementation."""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.services.tag_cache import TagCacheService
from micro_cold_spray.api.communication.models.equipment import (
    GasState, VacuumState, FeederState, NozzleState, EquipmentState
)


class EquipmentService:
    """Service for equipment control."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize equipment service.
        
        Args:
            config: Service configuration
        """
        self._service_name = "equipment"
        self._version = "1.0.0"
        self._config = config
        self._tag_cache: Optional[TagCacheService] = None
        self._is_running = False
        self._start_time = None
        logger.info("EquipmentService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def initialize(self) -> None:
        """Initialize equipment service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Initialize tag cache
            if not self._tag_cache:
                logger.error("Tag cache service not initialized")
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Tag cache service not initialized"
                )

            # Wait for tag cache service to be ready
            if not self._tag_cache.is_running:
                logger.error("Tag cache service not running")
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Tag cache service not running"
                )

            logger.info("Equipment service initialized")

        except Exception as e:
            error_msg = f"Failed to initialize equipment service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start equipment service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Initialize if needed
            if not self._tag_cache or not self._tag_cache.is_running:
                await self.initialize()

            self._start_time = datetime.now()
            self._is_running = True
            logger.info("Equipment service started")

        except Exception as e:
            error_msg = f"Failed to start equipment service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop equipment service."""
        try:
            if not self.is_running:
                return

            self._is_running = False
            self._start_time = None
            logger.info("Equipment service stopped")

        except Exception as e:
            error_msg = f"Failed to stop equipment service: {str(e)}"
            logger.error(error_msg)
            # Don't raise during shutdown

    def set_tag_cache(self, tag_cache: TagCacheService) -> None:
        """Set tag cache service.
        
        Args:
            tag_cache: Tag cache service instance
        """
        self._tag_cache = tag_cache

    async def get_gas_state(self) -> GasState:
        """Get gas system state.
        
        Returns:
            Gas system state
            
        Raises:
            HTTPException: If read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Read gas flow rates and valve states
            main_flow = await self._tag_cache.read_tag("gas_control.main_flow.measured")
            feeder_flow = await self._tag_cache.read_tag("gas_control.feeder_flow.measured")
            main_valve = await self._tag_cache.read_tag("valve_control.main_gas")
            feeder_valve = await self._tag_cache.read_tag("valve_control.feeder_gas")

            return GasState(
                main_flow=main_flow,
                feeder_flow=feeder_flow,
                main_valve=main_valve,
                feeder_valve=feeder_valve
            )

        except Exception as e:
            error_msg = "Failed to get gas state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def get_vacuum_state(self) -> VacuumState:
        """Get vacuum system state.
        
        Returns:
            Vacuum system state
            
        Raises:
            HTTPException: If read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Read vacuum system state
            chamber_pressure = await self._tag_cache.read_tag("pressure.chamber_pressure")
            gate_valve = await self._tag_cache.read_tag("valve_control.gate_valve.open")
            mech_pump = await self._tag_cache.read_tag("vacuum_control.mechanical_pump.start")
            booster_pump = await self._tag_cache.read_tag("vacuum_control.booster_pump.start")

            return VacuumState(
                chamber_pressure=chamber_pressure,
                gate_valve=gate_valve,
                mech_pump=mech_pump,
                booster_pump=booster_pump
            )

        except Exception as e:
            error_msg = "Failed to get vacuum state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def get_feeder_state(self, feeder_id: int) -> FeederState:
        """Get feeder state.
        
        Args:
            feeder_id: Feeder number (1 or 2)
            
        Returns:
            Feeder state
            
        Raises:
            HTTPException: If read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate feeder ID
            if feeder_id not in [1, 2]:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid feeder ID: {feeder_id}"
                )

            # Read feeder state
            frequency = await self._tag_cache.read_tag(f"gas_control.hardware_sets.set{feeder_id}.feeder.frequency")
            
            # Get running state from SSH P-tag
            start_var = f"P{10 if feeder_id == 1 else 110}"  # P10 or P110
            running = await self._tag_cache.read_tag(f"ssh.{start_var}")
            running = running == 1  # 1 = running, 4 = stopped

            return FeederState(
                running=running,
                frequency=frequency
            )

        except Exception as e:
            error_msg = f"Failed to get feeder {feeder_id} state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def get_nozzle_state(self) -> NozzleState:
        """Get nozzle state.
        
        Returns:
            Nozzle state
            
        Raises:
            HTTPException: If read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Read nozzle state
            selected = await self._tag_cache.read_tag("gas_control.hardware_sets.nozzle_select")
            shutter = await self._tag_cache.read_tag("relay_control.shutter")

            return NozzleState(
                selected=selected,  # False = nozzle 1, True = nozzle 2
                shutter=shutter
            )

        except Exception as e:
            error_msg = "Failed to get nozzle state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def get_state(self) -> EquipmentState:
        """Get current equipment state.
        
        Returns:
            Current equipment state
            
        Raises:
            HTTPException: If read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Read gas flow rates
            logger.debug("Reading gas flow rates...")
            feeder_flow = await self._tag_cache.read_tag("gas_control.feeder_flow.measured")
            logger.debug(f"Feeder flow = {feeder_flow}")
            main_flow = await self._tag_cache.read_tag("gas_control.main_flow.measured")
            logger.debug(f"Main flow = {main_flow}")

            # Read gas flow setpoints
            logger.debug("Reading gas flow setpoints...")
            feeder_setpoint = await self._tag_cache.read_tag("gas_control.feeder_flow.setpoint")
            logger.debug(f"Feeder setpoint = {feeder_setpoint}")
            main_setpoint = await self._tag_cache.read_tag("gas_control.main_flow.setpoint")
            logger.debug(f"Main setpoint = {main_setpoint}")

            # Read nozzle state
            logger.debug("Reading nozzle state...")
            nozzle_select = await self._tag_cache.read_tag("gas_control.hardware_sets.nozzle_select")
            logger.debug(f"Nozzle select = {nozzle_select}")
            shutter_engaged = await self._tag_cache.read_tag("interlocks.shutter_engaged")
            logger.debug(f"Shutter engaged = {shutter_engaged}")

            return EquipmentState(
                feeder_flow=feeder_flow,
                main_flow=main_flow,
                feeder_setpoint=feeder_setpoint,
                main_setpoint=main_setpoint,
                nozzle_select=2 if nozzle_select else 1,
                shutter_engaged=shutter_engaged
            )

        except Exception as e:
            error_msg = "Failed to get equipment state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_gas_flow(self, main_flow: Optional[float] = None, feeder_flow: Optional[float] = None) -> None:
        """Set gas flow rates.
        
        Args:
            main_flow: Main gas flow setpoint in SLPM
            feeder_flow: Feeder gas flow setpoint in SLPM
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Set flow rates if provided
            if main_flow is not None:
                await self._tag_cache.write_tag("gas_control.main_flow.setpoint", main_flow)
            
            if feeder_flow is not None:
                await self._tag_cache.write_tag("gas_control.feeder_flow.setpoint", feeder_flow)

        except Exception as e:
            error_msg = "Failed to set gas flow"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_gas_valves(self, main_valve: Optional[bool] = None, feeder_valve: Optional[bool] = None) -> None:
        """Set gas valve states.
        
        Args:
            main_valve: Main gas valve state
            feeder_valve: Feeder gas valve state
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Set valve states if provided
            if main_valve is not None:
                await self._tag_cache.write_tag("valve_control.main_gas", main_valve)
            
            if feeder_valve is not None:
                await self._tag_cache.write_tag("valve_control.feeder_gas", feeder_valve)

        except Exception as e:
            error_msg = "Failed to set gas valves"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_vacuum_pumps(self, mech_pump: Optional[bool] = None, booster_pump: Optional[bool] = None) -> None:
        """Set vacuum pump states.
        
        Args:
            mech_pump: Mechanical pump state
            booster_pump: Booster pump state
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Set pump states if provided
            if mech_pump is not None:
                if mech_pump:
                    await self._tag_cache.write_tag("vacuum_control.mechanical_pump.start", True)
                else:
                    await self._tag_cache.write_tag("vacuum_control.mechanical_pump.stop", True)
            
            if booster_pump is not None:
                if booster_pump:
                    await self._tag_cache.write_tag("vacuum_control.booster_pump.start", True)
                else:
                    await self._tag_cache.write_tag("vacuum_control.booster_pump.stop", True)

        except Exception as e:
            error_msg = "Failed to set vacuum pumps"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_gate_valve(self, position: str) -> None:
        """Set gate valve position.
        
        Args:
            position: Valve position ("open", "partial", "closed")
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate position
            if position not in ["open", "partial", "closed"]:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid gate valve position: {position}"
                )

            # Set valve position
            await self._tag_cache.write_tag("valve_control.gate_valve.open", position == "open")
            await self._tag_cache.write_tag("valve_control.gate_valve.partial", position == "partial")

        except Exception as e:
            error_msg = "Failed to set gate valve"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_feeder(self, feeder_id: int, frequency: Optional[float] = None, running: Optional[bool] = None) -> None:
        """Set feeder parameters.
        
        Args:
            feeder_id: Feeder number (1 or 2)
            frequency: Operating frequency in Hz
            running: Whether to start/stop feeder
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate feeder ID
            if feeder_id not in [1, 2]:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid feeder ID: {feeder_id}"
                )

            # Set frequency if provided
            if frequency is not None:
                await self._tag_cache.write_tag(f"gas_control.hardware_sets.set{feeder_id}.feeder.frequency", frequency)

            # Set running state if provided
            if running is not None:
                # Get SSH P-tag variables
                start_var = f"P{10 if feeder_id == 1 else 110}"  # P10 or P110
                await self._tag_cache.write_tag(f"ssh.{start_var}", 1 if running else 4)  # 1 = start, 4 = stop

        except Exception as e:
            error_msg = f"Failed to set feeder {feeder_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_deagglomerator(self, feeder_id: int, duty_cycle: float, frequency: float = 500) -> None:
        """Set deagglomerator parameters.
        
        Args:
            feeder_id: Feeder number (1 or 2)
            duty_cycle: PWM duty cycle (20-35%)
            frequency: PWM frequency (fixed at 500Hz)
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate feeder ID
            if feeder_id not in [1, 2]:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid feeder ID: {feeder_id}"
                )

            # Validate duty cycle
            if not 20 <= duty_cycle <= 35:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid duty cycle: {duty_cycle} (must be 20-35%)"
                )

            # Validate frequency
            if frequency != 500:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Frequency must be 500Hz"
                )

            # Set deagglomerator parameters
            await self._tag_cache.write_tag(f"gas_control.hardware_sets.set{feeder_id}.deagglomerator.duty_cycle", duty_cycle)
            await self._tag_cache.write_tag(f"gas_control.hardware_sets.set{feeder_id}.deagglomerator.frequency", frequency)

        except Exception as e:
            error_msg = f"Failed to set deagglomerator {feeder_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_nozzle(self, selected: Optional[bool] = None, shutter: Optional[bool] = None) -> None:
        """Set nozzle parameters.
        
        Args:
            selected: Nozzle selection (False=1, True=2)
            shutter: Shutter state
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Set nozzle selection if provided
            if selected is not None:
                await self._tag_cache.write_tag("gas_control.hardware_sets.nozzle_select", selected)

            # Set shutter state if provided
            if shutter is not None:
                await self._tag_cache.write_tag("relay_control.shutter", shutter)

        except Exception as e:
            error_msg = "Failed to set nozzle"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Health status dictionary
        """
        try:
            uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
            
            return {
                "status": "ok" if self.is_running else "error",
                "service": self._service_name,
                "version": self._version,
                "running": self.is_running,
                "uptime": uptime,
                "tag_cache": self._tag_cache is not None
            }
        except Exception as e:
            error_msg = "Failed to get health status"
            logger.error(f"{error_msg}: {str(e)}")
            return {
                "status": "error",
                "service": self._service_name,
                "version": self._version,
                "running": False,
                "error": str(e)
            }
