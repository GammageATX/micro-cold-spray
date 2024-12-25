"""Mock communication client for testing."""

from typing import Dict, Any
import random
from loguru import logger

from micro_cold_spray.api.communication.clients.base import CommunicationClient


class MockClient(CommunicationClient):
    """Mock client for testing without hardware."""

    # Simulated PLC tag values
    _plc_tags = {
        # Motion Control
        "AMC.Ax1Position": 0.0,  # X axis position
        "AMC.Ax2Position": 0.0,  # Y axis position
        "AMC.Ax3Position": 0.0,  # Z axis position
        "AMC.ModuleStatus": True,  # Motion controller ready
        "AMC.Ax1AxisStatus": 0x0090,  # X axis status (initialized & homed)
        "AMC.Ax2AxisStatus": 0x0090,  # Y axis status (initialized & homed)
        "AMC.Ax3AxisStatus": 0x0090,  # Z axis status (initialized & homed)
        
        # Motion Parameters
        "XAxis.Velocity": 50.0,
        "YAxis.Velocity": 50.0,
        "ZAxis.Velocity": 25.0,
        "XAxis.Accel": 100.0,
        "YAxis.Accel": 100.0,
        "ZAxis.Accel": 50.0,
        "XAxis.Decel": 100.0,
        "YAxis.Decel": 100.0,
        "ZAxis.Decel": 50.0,
        "XAxis.InProgress": False,
        "YAxis.InProgress": False,
        "ZAxis.InProgress": False,
        "XAxis.Complete": True,
        "YAxis.Complete": True,
        "ZAxis.Complete": True,
        
        # Gas Control
        "FeederFlowRate": 0.0,    # Measured feeder gas flow
        "MainFlowRate": 0.0,      # Measured main gas flow
        "AOS32-0.1.2.1": 0.0,     # Main gas flow setpoint
        "AOS32-0.1.2.2": 0.0,     # Feeder gas flow setpoint
        "MainGasValve": False,    # Main gas valve state
        "FeederGasValve": False,  # Feeder gas valve state
        
        # Hardware Sets
        "NozzleSelect": False,  # False=1, True=2
        "AOS32-0.1.6.1": 35,    # Deagglomerator 1 duty cycle (35=off)
        "AOS32-0.1.6.2": 500,   # Deagglomerator 1 frequency
        "AOS32-0.1.6.3": 35,    # Deagglomerator 2 duty cycle (35=off)
        "AOS32-0.1.6.4": 500,   # Deagglomerator 2 frequency
        
        # Pressure
        "ChamberPressure": 0.0,
        "FeederPressure": 0.0,
        "MainGasPressure": 0.0,
        "NozzlePressure": 0.0,
        "RegulatorPressure": 0.0,
        
        # Valves and Pumps
        "FeederSwitch": False,
        "MainSwitch": False,
        "VentSwitch": False,
        "GateValveOpen": False,     # Gate valve open state
        "GateValvePartial": False,  # Gate valve partial state
        "BoosterPumpStart": False,  # Booster pump start state
        "MechPumpStart": False,     # Mechanical pump start state
        
        # Shutter
        "Shutter": False,  # Shutter state
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize mock client.
        
        Args:
            config: Client configuration
        """
        super().__init__(config)
        
        # Extract mock config
        mock_config = config["communication"]["hardware"]["network"]["plc"]
        self._tag_file = mock_config["tag_file"]
        logger.info("Initialized mock client")

    async def connect(self) -> None:
        """Connect mock client."""
        self._connected = True
        logger.info("Connected mock client")

    async def disconnect(self) -> None:
        """Disconnect mock client."""
        self._connected = False
        logger.info("Disconnected mock client")

    async def read_tag(self, tag: str) -> Any:
        """Read mock tag value.
        
        Args:
            tag: Tag name
            
        Returns:
            Mock tag value
        """
        if not self._connected:
            raise RuntimeError("Mock client not connected")
            
        if tag not in self._plc_tags:
            raise KeyError(f"Tag {tag} not found")
            
        return self._plc_tags[tag]

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write mock tag value.
        
        Args:
            tag: Tag name
            value: Value to write
        """
        if not self._connected:
            raise RuntimeError("Mock client not connected")
            
        if tag not in self._plc_tags:
            raise KeyError(f"Tag {tag} not found")
            
        self._plc_tags[tag] = value
        logger.debug(f"Wrote mock tag {tag} = {value}")

    async def get(self) -> Dict[str, Any]:
        """Get all mock tag values.
        
        Returns:
            Dict of tag values
        """
        if not self._connected:
            raise RuntimeError("Mock client not connected")
            
        # Add some random noise to analog values
        for tag in self._plc_tags:
            if isinstance(self._plc_tags[tag], (int, float)):
                self._plc_tags[tag] += random.uniform(-0.1, 0.1)
                
        return self._plc_tags.copy()
