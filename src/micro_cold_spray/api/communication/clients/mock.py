"""Mock clients for testing and development."""

import asyncio
from typing import Any, Dict
from loguru import logger

from .base import CommunicationClient


class MockPLCClient(CommunicationClient):
    """Mock PLC client for testing."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize mock PLC client.
        
        Args:
            config: Configuration dict (can be empty for mock clients)
        """
        super().__init__("mock_plc", config)
        self._tag_values: Dict[str, Any] = {}
        self._initialize_default_values()
        logger.info("MockPLCClient initialized")

    def _initialize_default_values(self) -> None:
        """Initialize default values for a freshly started system.
        
        Note: Values are stored in their native PLC format:
        - Boolean tags are stored as Python booleans (True/False)
        - Analog tags are stored as raw 12-bit integers (0-4095)
        """
        # System Status Tags (Boolean values)
        self._tag_values.update({
            "MainSwitch": False,      # Main Gas Valve (False=closed)
            "FeederSwitch": False,    # Feeder Gas Valve (False=closed)
            "VentSwitch": False,      # Chamber Vent Valve (False=closed)
            "NozzleSelect": False,    # Nozzle selection (False=nozzle1, True=nozzle2)
        })

        # Motion Control Tags (Boolean and raw values)
        self._tag_values.update({
            "XAxis.InProgress": False,  # False=not moving
            "YAxis.InProgress": False,
            "ZAxis.InProgress": False,
            "XAxis.Complete": False,    # False=not complete
            "YAxis.Complete": False,
            "ZAxis.Complete": False,
            "AMC.Ax1Position": 0,       # Raw encoder counts
            "AMC.Ax2Position": 0,
            "AMC.Ax3Position": 0,
            "XAxis.Status": 0,          # Status codes
            "YAxis.Status": 0,
            "ZAxis.Status": 0,
        })

        # Pressure and Flow Tags (12-bit values 0-4095)
        self._tag_values.update({
            "MainGasPressure": 4095,    # 100 psi = 4095 (full scale)
            "RegulatorPressure": 3276,  # 80 psi = (80/100) * 4095
            "FeederPressure": 819,      # 0.2 torr = (0.2/1.0) * 4095
            "MainFlowRate": 0,          # 0 SLPM = 0
            "FeederFlowRate": 0,        # 0 SLPM = 0
            "ChamberPressure": 409,     # 0.1 torr = (0.1/1.0) * 4095
            "NozzlePressure": 819,      # 0.2 torr = (0.2/1.0) * 4095
        })

        # Pump Control Tags (Boolean values)
        self._tag_values.update({
            "MechPumpStart": False,    # False=not started
            "MechPumpStop": False,     # False=not stopped
            "BoosterPumpStart": False,
            "BoosterPumpStop": False,
        })

        # Shutter Control Tags (Boolean values)
        self._tag_values.update({
            "Shutter": False,   # False=not engaged
            "Open": False,      # False=not open
            "Partial": False,   # False=not partial
        })

        logger.info("Initialized mock PLC with default values for fresh system start")

    async def connect(self) -> None:
        """Mock connect - always succeeds."""
        await asyncio.sleep(0.1)  # Simulate connection delay
        self._connected = True
        logger.debug("MockPLCClient connected")

    async def disconnect(self) -> None:
        """Mock disconnect - always succeeds."""
        await asyncio.sleep(0.1)  # Simulate disconnection delay
        self._connected = False
        logger.debug("MockPLCClient disconnected")

    async def read_tag(self, tag: str) -> Any:
        """Read mock tag value."""
        await asyncio.sleep(0.05)  # Simulate read delay
        return self._tag_values.get(tag, 0)  # Default to 0 for unknown tags

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write mock tag value.
        
        Note: Values are stored in their native PLC format:
        - Boolean tags accept Python booleans (True/False)
        - Analog tags accept raw 12-bit integers (0-4095)
        """
        await asyncio.sleep(0.05)  # Simulate write delay
        if tag in self._tag_values:  # Only allow writing to known tags
            # Validate value range based on tag type
            if tag in [
                "MainGasPressure",
                "RegulatorPressure",
                "FeederPressure",
                "MainFlowRate",
                "FeederFlowRate",
                "ChamberPressure",
                "NozzlePressure"
            ]:
                # Analog values should be 12-bit (0-4095)
                value = max(0, min(4095, int(value)))
            elif isinstance(self._tag_values[tag], bool):
                # Boolean tags should be True/False
                value = bool(value)
                
            self._tag_values[tag] = value
            logger.debug(f"MockPLCClient wrote {tag}={value}")
        else:
            logger.warning(f"Attempted to write to unknown tag: {tag}")


class MockSSHClient(CommunicationClient):
    """Mock SSH client for testing."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize mock SSH client."""
        super().__init__("mock_ssh", config)
        self._tag_values: Dict[str, Any] = {}
        self._initialize_default_values()
        logger.info("MockSSHClient initialized")

    def _initialize_default_values(self) -> None:
        """Initialize default values for a freshly started system.
        
        Note: P tag values for both feeders:
        - P6/P106: Frequency (200-1200 Hz)
        - P10/P110: Start/Stop (1=start, 4=stop)
        - P12/P112: Run time (999 default)
        """
        # Feeder 1 P tags
        self._tag_values.update({
            "P6": 200,    # Initial frequency at minimum (200 Hz)
            "P10": 4,     # Initially stopped (4)
            "P12": 999,   # Default run time (999 seconds)
        })

        # Feeder 2 P tags
        self._tag_values.update({
            "P106": 200,  # Initial frequency at minimum (200 Hz)
            "P110": 4,    # Initially stopped (4)
            "P112": 999,  # Default run time (999 seconds)
        })

        logger.info("Initialized mock SSH with default P tag values")

    async def connect(self) -> None:
        """Mock connect - always succeeds."""
        await asyncio.sleep(0.1)  # Simulate connection delay
        self._connected = True
        logger.debug("MockSSHClient connected")

    async def disconnect(self) -> None:
        """Mock disconnect - always succeeds."""
        await asyncio.sleep(0.1)  # Simulate disconnection delay
        self._connected = False
        logger.debug("MockSSHClient disconnected")

    async def read_tag(self, tag: str) -> Any:
        """Read mock tag value."""
        await asyncio.sleep(0.05)  # Simulate read delay
        return self._tag_values.get(tag, 0)  # Default to 0 for unknown tags

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write mock tag value.
        
        Note: P tag validation:
        - P6/P106: Must be between 200-1200
        - P10/P110: Must be 1 (start) or 4 (stop)
        - P12/P112: Must be positive integer
        """
        await asyncio.sleep(0.05)  # Simulate write delay
        if tag in self._tag_values:  # Only allow writing to known tags
            # Validate value based on tag type
            if tag in ["P6", "P106"]:  # Frequency tags
                value = max(200, min(1200, int(value)))
            elif tag in ["P10", "P110"]:  # Start/Stop tags
                value = 4 if value == 4 else 1  # Only allow 1 or 4
            elif tag in ["P12", "P112"]:  # Time tags
                value = max(0, int(value))  # Must be positive integer
                
            self._tag_values[tag] = value
            logger.debug(f"MockSSHClient wrote {tag}={value}")
        else:
            logger.warning(f"Attempted to write to unknown tag: {tag}")
