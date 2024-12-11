"""Mock hardware client implementations."""

import asyncio
from typing import Any, Dict
from loguru import logger

from .. import HardwareError


class MockPLCClient:
    """Mock PLC client that simulates basic hardware behavior."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize mock PLC client."""
        self._config = config
        self._connected = False
        self._tag_values = {
            "AMC.Ax1Position": 0.0,
            "AMC.Ax2Position": 0.0,
            "AOS32-0.1.2.1": 0.0,
            "FeederFlowRate": 0.0,
            "FeederSwitch": False,
            "VentSwitch": False,
            "Partial": False,
            "Open": False,
            "Shutter": False
        }
        logger.info("MockPLCClient initialized")

    async def connect(self) -> None:
        """Connect to simulated PLC."""
        await asyncio.sleep(0.1)  # Simulate network delay
        self._connected = True
        logger.info("MockPLCClient connected")

    async def disconnect(self) -> None:
        """Disconnect from simulated PLC."""
        await asyncio.sleep(0.1)  # Simulate network delay
        self._connected = False
        logger.info("MockPLCClient disconnected")

    async def read_tag(self, tag_name: str) -> Any:
        """Read value from simulated tag."""
        if not self._connected:
            raise HardwareError(
                "Not connected to PLC",
                "plc",
                {
                    "operation": "read_tag",
                    "tag": tag_name,
                    "connected": False
                }
            )
        await asyncio.sleep(0.1)  # Simulate network delay
        if tag_name in self._tag_values:
            return self._tag_values[tag_name]
        else:
            return 0  # Default value for unknown tags

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Write value to simulated tag."""
        if not self._connected:
            raise HardwareError(
                "Not connected to PLC",
                "plc",
                {
                    "operation": "write_tag",
                    "tag": tag_name,
                    "connected": False
                }
            )
        await asyncio.sleep(0.1)  # Simulate network delay
        self._tag_values[tag_name] = value
        logger.debug(f"MockPLC wrote {value} to {tag_name}")


class MockSSHClient:
    """Mock SSH client that simulates feeder controller behavior."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize mock SSH client."""
        self._config = config
        self._connected = False
        self._last_command = ""
        logger.info("MockSSHClient initialized")

    async def connect(self) -> None:
        """Connect to simulated feeder controller."""
        await asyncio.sleep(0.1)  # Simulate network delay
        self._connected = True
        logger.info("MockSSHClient connected")

    async def disconnect(self) -> None:
        """Disconnect from simulated feeder controller."""
        await asyncio.sleep(0.1)  # Simulate network delay
        self._connected = False
        logger.info("MockSSHClient disconnected")

    async def write_command(self, command: str) -> None:
        """Write command to simulated feeder controller."""
        if not self._connected:
            raise HardwareError(
                "Not connected to feeder controller",
                "feeder",
                {
                    "operation": "write_command",
                    "connected": False
                }
            )
        await asyncio.sleep(0.1)  # Simulate network delay
        self._last_command = command
        logger.debug(f"MockSSH command: {command}")

    async def read_response(self) -> str:
        """Read response from simulated feeder controller."""
        if not self._connected:
            raise HardwareError(
                "Not connected to feeder controller",
                "feeder",
                {
                    "operation": "read_response",
                    "connected": False
                }
            )
        await asyncio.sleep(0.1)  # Simulate network delay
        return "OK"
