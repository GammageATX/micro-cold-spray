"""Equipment control service implementation."""

from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error


class EquipmentService:
    """Service for controlling equipment state."""

    def __init__(self):
        """Initialize equipment service."""
        self._service_name = "equipment"
        self._is_running = False
        self._gas_running = False
        self._vacuum_running = False
        self._feeder_running = False
        self._nozzle_running = False
        logger.info("EquipmentService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def start(self) -> None:
        """Start equipment service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

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
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running"
                )

            # Stop all subsystems
            if self._gas_running:
                await self.stop_gas()
            if self._vacuum_running:
                await self.stop_vacuum()
            if self._feeder_running:
                await self.stop_feeder()
            if self._nozzle_running:
                await self.stop_nozzle()

            self._is_running = False
            logger.info("Equipment service stopped")

        except Exception as e:
            error_msg = f"Failed to stop equipment service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def get_state(self) -> Dict[str, Any]:
        """Get current equipment state.
        
        Returns:
            Current equipment state
            
        Raises:
            HTTPException: If state cannot be retrieved
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            return {
                "gas": {
                    "running": self._gas_running
                },
                "vacuum": {
                    "running": self._vacuum_running
                },
                "feeder": {
                    "running": self._feeder_running
                },
                "nozzle": {
                    "running": self._nozzle_running
                }
            }

        except Exception as e:
            error_msg = "Failed to get equipment state"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def start_gas(self) -> None:
        """Start gas system.
        
        Raises:
            HTTPException: If start fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if self._gas_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Gas system already running"
                )

            self._gas_running = True
            logger.info("Gas system started")

        except Exception as e:
            error_msg = "Failed to start gas system"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def stop_gas(self) -> None:
        """Stop gas system.
        
        Raises:
            HTTPException: If stop fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if not self._gas_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Gas system not running"
                )

            self._gas_running = False
            logger.info("Gas system stopped")

        except Exception as e:
            error_msg = "Failed to stop gas system"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def start_vacuum(self) -> None:
        """Start vacuum system.
        
        Raises:
            HTTPException: If start fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if self._vacuum_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Vacuum system already running"
                )

            self._vacuum_running = True
            logger.info("Vacuum system started")

        except Exception as e:
            error_msg = "Failed to start vacuum system"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def stop_vacuum(self) -> None:
        """Stop vacuum system.
        
        Raises:
            HTTPException: If stop fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if not self._vacuum_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Vacuum system not running"
                )

            self._vacuum_running = False
            logger.info("Vacuum system stopped")

        except Exception as e:
            error_msg = "Failed to stop vacuum system"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def start_feeder(self) -> None:
        """Start powder feeder.
        
        Raises:
            HTTPException: If start fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if self._feeder_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Powder feeder already running"
                )

            self._feeder_running = True
            logger.info("Powder feeder started")

        except Exception as e:
            error_msg = "Failed to start powder feeder"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def stop_feeder(self) -> None:
        """Stop powder feeder.
        
        Raises:
            HTTPException: If stop fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if not self._feeder_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Powder feeder not running"
                )

            self._feeder_running = False
            logger.info("Powder feeder stopped")

        except Exception as e:
            error_msg = "Failed to stop powder feeder"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def start_nozzle(self) -> None:
        """Start spray nozzle.
        
        Raises:
            HTTPException: If start fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if self._nozzle_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Spray nozzle already running"
                )

            self._nozzle_running = True
            logger.info("Spray nozzle started")

        except Exception as e:
            error_msg = "Failed to start spray nozzle"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def stop_nozzle(self) -> None:
        """Stop spray nozzle.
        
        Raises:
            HTTPException: If stop fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if not self._nozzle_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Spray nozzle not running"
                )

            self._nozzle_running = False
            logger.info("Spray nozzle stopped")

        except Exception as e:
            error_msg = "Failed to stop spray nozzle"
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
        return {
            "status": "ok" if self.is_running else "error",
            "service": self._service_name,
            "running": self.is_running
        }
