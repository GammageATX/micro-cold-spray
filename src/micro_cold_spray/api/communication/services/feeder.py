"""Feeder control service."""

from typing import Dict, Any
from loguru import logger

from ...base import BaseService
from ..exceptions import HardwareError
from ..clients import PLCClient


class FeederService(BaseService):
    """Service for controlling powder feeder."""

    def __init__(self, plc_client: PLCClient):
        """Initialize feeder service.
        
        Args:
            plc_client: PLC client for hardware communication
        """
        super().__init__(service_name="feeder")
        self._plc = plc_client
        self._running = False

    async def start_feeder(self) -> None:
        """Start powder feeder.
        
        Raises:
            HardwareError: If start fails
        """
        try:
            await self._plc.write_tag("feeder.start", True)
            self._running = True
            logger.info("Feeder started")
        except Exception as e:
            raise HardwareError(
                "Failed to start feeder",
                "feeder",
                {"error": str(e)}
            )

    async def stop_feeder(self) -> None:
        """Stop powder feeder.
        
        Raises:
            HardwareError: If stop fails
        """
        try:
            await self._plc.write_tag("feeder.start", False)
            self._running = False
            logger.info("Feeder stopped")
        except Exception as e:
            raise HardwareError(
                "Failed to stop feeder",
                "feeder",
                {"error": str(e)}
            )

    async def set_speed(self, speed: float) -> None:
        """Set feeder speed.
        
        Args:
            speed: Speed setpoint (0-100%)
            
        Raises:
            HardwareError: If setting speed fails
            ValueError: If speed out of range
        """
        if not 0 <= speed <= 100:
            raise ValueError("Speed must be between 0 and 100%")
            
        try:
            await self._plc.write_tag("feeder.speed", speed)
            logger.info(f"Feeder speed set to {speed}%")
        except Exception as e:
            raise HardwareError(
                "Failed to set feeder speed",
                "feeder",
                {
                    "speed": speed,
                    "error": str(e)
                }
            )

    async def get_status(self) -> Dict[str, Any]:
        """Get feeder status.
        
        Returns:
            Dictionary with feeder status
            
        Raises:
            HardwareError: If reading status fails
        """
        try:
            speed = await self._plc.read_tag("feeder.speed")
            running = await self._plc.read_tag("feeder.running")
            error = await self._plc.read_tag("feeder.error")
            
            return {
                "running": running,
                "speed": speed,
                "error": error
            }
        except Exception as e:
            raise HardwareError(
                "Failed to get feeder status",
                "feeder",
                {"error": str(e)}
            )
