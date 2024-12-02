"""Mock hardware client implementations."""
import asyncio
from typing import Any, Dict
from loguru import logger


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

    async def get_all_tags(self) -> Dict[str, Any]:
        """Get all simulated tag values."""
        if not self._connected:
            raise RuntimeError("Not connected to PLC")
        await asyncio.sleep(0.1)  # Simulate network delay
        return self._tag_values.copy()

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Write value to simulated tag."""
        if not self._connected:
            raise RuntimeError("Not connected to PLC")
        await asyncio.sleep(0.1)  # Simulate network delay
        if tag_name in self._tag_values:
            self._tag_values[tag_name] = value
            logger.debug(f"MockPLC wrote {value} to {tag_name}")
        else:
            logger.warning(f"MockPLC: Unknown tag {tag_name}")


class MockSSHClient:
    """Mock SSH client that simulates feeder controller behavior."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize mock SSH client."""
        self._config = config
        self._connected = False
        self._last_command = ""
        logger.info("MockSSHClient initialized")

    async def test_connection(self) -> bool:
        """Test simulated connection."""
        await asyncio.sleep(0.1)  # Simulate network delay
        return self._connected

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
            raise RuntimeError("Not connected to feeder controller")
        await asyncio.sleep(0.1)  # Simulate network delay
        self._last_command = command
        logger.debug(f"MockSSH command: {command}")

    async def read_response(self) -> str:
        """Read response from simulated feeder controller."""
        if not self._connected:
            raise RuntimeError("Not connected to feeder controller")
        await asyncio.sleep(0.1)  # Simulate network delay
        return "OK"
