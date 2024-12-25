"""Equipment service implementation."""

from typing import Dict, Any, Optional, Callable, List
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
        self._state_callbacks: List[Callable[[EquipmentState], None]] = []
        logger.info("\n EquipmentService initialized")

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

            # Register for state updates
            self._tag_cache.add_state_callback(self._handle_state_change)

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

            # Unregister state callback
            if self._tag_cache:
                self._tag_cache.remove_state_callback(self._handle_state_change)

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

    def _handle_state_change(self, state_type: str, state: Any) -> None:
        """Handle state change from tag cache.
        
        Args:
            state_type: Type of state that changed
            state: New state value
        """
        if state_type == "equipment":
            # Notify equipment state callbacks
            for callback in self._state_callbacks:
                try:
                    callback(state)
                except Exception as e:
                    logger.error(f"Error in equipment state callback: {str(e)}")

    def on_state_changed(self, callback: Callable[[EquipmentState], None]) -> None:
        """Register callback for equipment state changes.
        
        Args:
            callback: Function to call when state changes
        """
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)

    def remove_state_changed_callback(self, callback: Callable[[EquipmentState], None]) -> None:
        """Remove state change callback.
        
        Args:
            callback: Callback to remove
        """
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    async def get_state(self) -> EquipmentState:
        """Get complete equipment state.
        
        Returns:
            Equipment state
            
        Raises:
            HTTPException: If read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Get cached equipment state
            state = await self._tag_cache.get_state("equipment")
            if not state:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Equipment state not available"
                )

            return state

        except Exception as e:
            error_msg = "Failed to get equipment state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

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

            # Get cached gas state
            state = await self._tag_cache.get_state("gas")
            if not state:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Gas state not available"
                )

            return state

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

            # Get cached vacuum state
            state = await self._tag_cache.get_state("vacuum")
            if not state:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Vacuum state not available"
                )

            return state

        except Exception as e:
            error_msg = "Failed to get vacuum state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_main_flow(self, flow_rate: float) -> None:
        """Set main gas flow rate.
        
        Args:
            flow_rate: Flow rate in SLPM
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Write flow rate setpoint
            await self._tag_cache.set_tag("gas_control.main_flow.setpoint", flow_rate)
            logger.info(f"Set main gas flow to {flow_rate} SLPM")

        except Exception as e:
            error_msg = "Failed to set main flow"
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

            # Get cached feeder state
            state = await self._tag_cache.get_state(f"feeder{feeder_id}")
            if not state:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Feeder {feeder_id} state not available"
                )

            return state

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

            # Get cached nozzle state
            state = await self._tag_cache.get_state("nozzle")
            if not state:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Nozzle state not available"
                )

            return state

        except Exception as e:
            error_msg = "Failed to get nozzle state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_feeder_flow(self, flow_rate: float) -> None:
        """Set feeder gas flow rate.
        
        Args:
            flow_rate: Flow rate in SLPM
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Write flow rate setpoint
            await self._tag_cache.set_tag("gas_control.feeder_flow.setpoint", flow_rate)
            logger.info(f"Set feeder gas flow to {flow_rate} SLPM")

        except Exception as e:
            error_msg = "Failed to set feeder flow"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Dict[str, Any]: Health status dictionary
        """
        try:
            return {
                "status": "ok" if self.is_running else "error",
                "service_name": self._service_name,
                "version": self._version,
                "is_running": self.is_running,
                "uptime": (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
                "error": None if self.is_running else "Service not running",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            error_msg = f"Failed to get health status: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "service_name": self._service_name,
                "version": self._version,
                "is_running": False,
                "uptime": 0,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }

    async def set_feeder_frequency(self, feeder_id: int, frequency: float) -> None:
        """Set feeder frequency.
        
        Args:
            feeder_id: Feeder ID (1 or 2)
            frequency: Frequency in Hz
            
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

            # Write frequency setpoint
            await self._tag_cache.set_tag(f"feeder{feeder_id}.frequency.setpoint", frequency)
            logger.info(f"Set feeder {feeder_id} frequency to {frequency} Hz")

        except Exception as e:
            error_msg = f"Failed to set feeder {feeder_id} frequency"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def start_feeder(self, feeder_id: int) -> None:
        """Start feeder.
        
        Args:
            feeder_id: Feeder ID (1 or 2)
            
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

            # Write start command
            await self._tag_cache.set_tag(f"feeder{feeder_id}.start", True)
            logger.info(f"Started feeder {feeder_id}")

        except Exception as e:
            error_msg = f"Failed to start feeder {feeder_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def stop_feeder(self, feeder_id: int) -> None:
        """Stop feeder.
        
        Args:
            feeder_id: Feeder ID (1 or 2)
            
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

            # Write stop command
            await self._tag_cache.set_tag(f"feeder{feeder_id}.start", False)
            logger.info(f"Stopped feeder {feeder_id}")

        except Exception as e:
            error_msg = f"Failed to stop feeder {feeder_id}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_deagg_speed(self, deagg_id: int, speed: float) -> None:
        """Set deagglomerator speed.
        
        Args:
            deagg_id: Deagglomerator ID (1 or 2)
            speed: Speed percentage (0-100)
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate deagglomerator ID
            if deagg_id not in [1, 2]:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid deagglomerator ID: {deagg_id}"
                )

            # Validate speed range
            if not 0 <= speed <= 100:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid speed: {speed}. Must be between 0 and 100"
                )

            # Write speed setpoint
            await self._tag_cache.set_tag(f"deagg{deagg_id}.speed.setpoint", speed)
            logger.info(f"Set deagglomerator {deagg_id} speed to {speed}%")

        except Exception as e:
            error_msg = f"Failed to set deagglomerator {deagg_id} speed"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def select_nozzle(self, nozzle_id: int) -> None:
        """Select active nozzle.
        
        Args:
            nozzle_id: Nozzle ID (1 or 2)
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate nozzle ID
            if nozzle_id not in [1, 2]:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid nozzle ID: {nozzle_id}"
                )

            # Write nozzle selection
            await self._tag_cache.set_tag("nozzle.selected", nozzle_id)
            logger.info(f"Selected nozzle {nozzle_id}")

        except Exception as e:
            error_msg = "Failed to select nozzle"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_shutter(self, open: bool) -> None:
        """Control nozzle shutter.
        
        Args:
            open: True to open shutter, False to close
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Write shutter command
            await self._tag_cache.set_tag("nozzle.shutter.open", open)
            logger.info(f"{'Opened' if open else 'Closed'} nozzle shutter")

        except Exception as e:
            error_msg = f"Failed to {'open' if open else 'close'} shutter"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_main_gas_valve(self, open: bool) -> None:
        """Control main gas valve.
        
        Args:
            open: True to open valve, False to close
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Write valve command
            await self._tag_cache.set_tag("gas_control.main_valve.open", open)
            logger.info(f"{'Opened' if open else 'Closed'} main gas valve")

        except Exception as e:
            error_msg = f"Failed to {'open' if open else 'close'} main gas valve"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_feeder_gas_valve(self, open: bool) -> None:
        """Control feeder gas valve.
        
        Args:
            open: True to open valve, False to close
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Write valve command
            await self._tag_cache.set_tag("gas_control.feeder_valve.open", open)
            logger.info(f"{'Opened' if open else 'Closed'} feeder gas valve")

        except Exception as e:
            error_msg = f"Failed to {'open' if open else 'close'} feeder gas valve"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_gate_valve_position(self, position: float) -> None:
        """Control gate valve position.
        
        Args:
            position: Valve position percentage (0-100)
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate position range
            if not 0 <= position <= 100:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid position: {position}. Must be between 0 and 100"
                )

            # Write position setpoint
            await self._tag_cache.set_tag("vacuum.gate_valve.position", position)
            logger.info(f"Set gate valve position to {position}%")

        except Exception as e:
            error_msg = "Failed to set gate valve position"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_vent_valve(self, open: bool) -> None:
        """Control vent valve.
        
        Args:
            open: True to open valve, False to close
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Write valve command
            await self._tag_cache.set_tag("vacuum.vent_valve.open", open)
            logger.info(f"{'Opened' if open else 'Closed'} vent valve")

        except Exception as e:
            error_msg = f"Failed to {'open' if open else 'close'} vent valve"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def start_mech_pump(self) -> None:
        """Start mechanical pump.
        
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Write pump command
            await self._tag_cache.set_tag("vacuum.mech_pump.start", True)
            logger.info("Started mechanical pump")

        except Exception as e:
            error_msg = "Failed to start mechanical pump"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def stop_mech_pump(self) -> None:
        """Stop mechanical pump.
        
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Write pump command
            await self._tag_cache.set_tag("vacuum.mech_pump.start", False)
            logger.info("Stopped mechanical pump")

        except Exception as e:
            error_msg = "Failed to stop mechanical pump"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def start_booster_pump(self) -> None:
        """Start booster pump.
        
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Write pump command
            await self._tag_cache.set_tag("vacuum.booster_pump.start", True)
            logger.info("Started booster pump")

        except Exception as e:
            error_msg = "Failed to start booster pump"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def stop_booster_pump(self) -> None:
        """Stop booster pump.
        
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Write pump command
            await self._tag_cache.set_tag("vacuum.booster_pump.start", False)
            logger.info("Stopped booster pump")

        except Exception as e:
            error_msg = "Failed to stop booster pump"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def set_deagglomerator(self, deagg_id: int, duty_cycle: float, frequency: float) -> None:
        """Set deagglomerator parameters.
        
        Args:
            deagg_id: Deagglomerator ID (1 or 2)
            duty_cycle: Duty cycle percentage (0-100)
            frequency: Frequency in Hz
            
        Raises:
            HTTPException: If write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Validate deagglomerator ID
            if deagg_id not in [1, 2]:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid deagglomerator ID: {deagg_id}"
                )

            # Validate duty cycle range
            if not 0 <= duty_cycle <= 100:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"Invalid duty cycle: {duty_cycle}. Must be between 0 and 100"
                )

            # Write parameters
            await self._tag_cache.set_tag(f"deagg{deagg_id}.duty_cycle.setpoint", duty_cycle)
            await self._tag_cache.set_tag(f"deagg{deagg_id}.frequency.setpoint", frequency)
            logger.info(f"Set deagglomerator {deagg_id} parameters: duty cycle={duty_cycle}%, frequency={frequency}Hz")

        except Exception as e:
            error_msg = f"Failed to set deagglomerator {deagg_id} parameters"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )
