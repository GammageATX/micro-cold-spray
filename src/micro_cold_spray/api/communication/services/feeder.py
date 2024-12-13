"""Feeder control service."""

from typing import Dict
from loguru import logger

from ...base import ConfigurableService
from ...base.exceptions import HardwareError, ValidationError
from ..clients import SSHClient


class FeederService(ConfigurableService):
    """Service for controlling powder feeder via P tags."""

    def __init__(self, ssh_client: SSHClient, hardware_set: int = 1):
        """Initialize feeder service.
        
        Args:
            ssh_client: SSH client for direct feeder control
            hardware_set: Hardware set number (1 or 2)
        """
        super().__init__(service_name="feeder")
        self._ssh = ssh_client
        self._hardware_set = hardware_set
        
        # Get P tag variables based on hardware set
        if hardware_set == 1:
            self._freq_var = "P6"
            self._start_var = "P10"
            self._time_var = "P12"
        else:
            self._freq_var = "P106"
            self._start_var = "P110"
            self._time_var = "P112"

    async def start_feeder(self, frequency: float) -> None:
        """Start powder feeder.
        
        Args:
            frequency: Feeder frequency (200-1200 Hz)
            
        Raises:
            HardwareError: If start fails
            ValidationError: If frequency out of range
        """
        if not 200 <= frequency <= 1200:
            raise ValidationError(
                "Frequency must be between 200 and 1200 Hz",
                {"frequency": frequency, "limits": (200, 1200)}
            )
            
        try:
            # Set frequency
            await self._ssh.execute_command(f"{self._freq_var}={frequency}")
            # Set run time to 999 seconds
            await self._ssh.execute_command(f"{self._time_var}=999")
            # Start feeder
            await self._ssh.execute_command(f"{self._start_var}=1")
            logger.info(f"Started feeder at {frequency} Hz")
        except Exception as e:
            raise HardwareError(
                "Failed to start feeder",
                "feeder",
                {
                    "frequency": frequency,
                    "error": str(e)
                }
            )

    async def stop_feeder(self) -> None:
        """Stop powder feeder.
        
        Raises:
            HardwareError: If stop fails
        """
        try:
            await self._ssh.execute_command(f"{self._start_var}=4")
            logger.info("Stopped feeder")
        except Exception as e:
            raise HardwareError(
                "Failed to stop feeder",
                "feeder",
                {"error": str(e)}
            )

    async def get_status(self) -> Dict[str, float]:
        """Get feeder frequency setting.
        
        Returns:
            Dictionary with current frequency setting
            
        Raises:
            HardwareError: If reading fails
        """
        try:
            freq = await self._ssh.execute_command(f"echo ${self._freq_var}")
            return {"frequency": float(freq)}
        except Exception as e:
            raise HardwareError(
                "Failed to get feeder status",
                "feeder",
                {"error": str(e)}
            )
