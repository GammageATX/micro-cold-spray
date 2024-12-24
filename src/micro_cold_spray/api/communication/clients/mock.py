"""Mock communication client."""

import asyncio
import random
from typing import Any, Dict
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
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
        "FeederFlowRate": 0.0,
        "MainFlowRate": 0.0,
        "AOS32-0.1.2.1": 0.0,  # Main gas flow setpoint
        "AOS32-0.1.2.2": 0.0,  # Feeder gas flow setpoint
        
        # Hardware Sets
        "NozzleSelect": False,  # False=1, True=2
        "AOS32-0.1.6.1": 35,  # Deagglomerator 1 duty cycle (35=off)
        "AOS32-0.1.6.2": 500,  # Deagglomerator 1 frequency
        "AOS32-0.1.6.3": 35,  # Deagglomerator 2 duty cycle (35=off)
        "AOS32-0.1.6.4": 500,  # Deagglomerator 2 frequency
        
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
        "Open": False,
        "Partial": False,
        "BoosterPumpStart": False,
        "BoosterPumpStop": False,
        "MechPumpStart": False,
        "MechPumpStop": False,
        
        # Shutter
        "Shutter": False
    }
    
    # Simulated SSH (feeder) tag values for both feeders
    _ssh_tags = {
        # Feeder 1
        "P6": 200,    # Frequency (200-1200 Hz)
        "P10": 4,     # Start/Stop (1=start, 4=stop)
        "P12": 999,   # Time
        
        # Feeder 2
        "P106": 200,  # Frequency (200-1200 Hz)
        "P110": 4,    # Start/Stop (1=start, 4=stop)
        "P112": 999   # Time
    }
    
    # Simulated delays (seconds)
    _delays = {
        "connect": (0.1, 0.2),      # Connect delay range
        "disconnect": (0.1, 0.2),    # Disconnect delay range
        "read": (0.05, 0.1),        # Read delay range
        "write": (0.05, 0.1)        # Write delay range
    }
    
    # Error simulation (disabled)
    _error_rates = {
        "connect": 0.0,    # Disabled
        "read": 0.0,       # Disabled
        "write": 0.0       # Disabled
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize mock client.
        
        Args:
            config: Client configuration from communication.yaml
        """
        super().__init__(config)
        
        # Determine client type from config
        self._client_type = "plc"  # Default to PLC
        self._tag_values = self._plc_tags  # Default to PLC tags
        
        if "communication" in config and "hardware" in config["communication"]:
            network = config["communication"]["hardware"]["network"]
            if "plc" in network:
                self._client_type = "plc"
                self._tag_values = self._plc_tags
            elif "ssh" in network:
                self._client_type = "ssh"
                self._tag_values = self._ssh_tags
            else:
                self._client_type = "unknown"
                self._tag_values = {}
                
        # Get mock delay from config
        self._mock_delay = config["communication"]["hardware"]["network"]["mock"]["delay"]
        
        logger.info(f"Initialized mock {self._client_type} client")
        
    async def _simulate_delay(self, operation: str) -> None:
        """Simulate realistic operation delay.
        
        Args:
            operation: Operation type (connect, disconnect, read, write)
        """
        min_delay, max_delay = self._delays[operation]
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
        
    def _simulate_error(self, operation: str) -> None:
        """Simulate random operation errors.
        
        Args:
            operation: Operation type (connect, read, write)
            
        Raises:
            HTTPException: If error is simulated
        """
        if operation in self._error_rates:
            if random.random() < self._error_rates[operation]:
                error_msg = f"Simulated {operation} error for {self._client_type} client"
                logger.warning(error_msg)
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message=error_msg
                )

    async def connect(self) -> None:
        """Connect mock client.
        
        Raises:
            HTTPException: If connection fails
        """
        # Simulate connection delay and possible error
        await self._simulate_delay("connect")
        self._simulate_error("connect")
        
        self._connected = True
        logger.info(f"Connected mock {self._client_type} client")

    async def disconnect(self) -> None:
        """Disconnect mock client."""
        # Simulate disconnect delay
        await self._simulate_delay("disconnect")
        
        self._connected = False
        logger.info(f"Disconnected mock {self._client_type} client")

    async def read_tag(self, tag: str) -> Any:
        """Read mock tag value.
        
        Args:
            tag: Tag name to read
            
        Returns:
            Tag value
            
        Raises:
            HTTPException: If read fails or tag not found
        """
        # Check connection
        if not self._connected:
            logger.error(f"Mock {self._client_type} client not connected")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Mock {self._client_type} client not connected"
            )
            
        # Simulate read delay and possible error
        await self._simulate_delay("read")
        self._simulate_error("read")
        
        # Get tag value
        if tag not in self._tag_values:
            logger.error(f"Tag '{tag}' not found in {self._client_type} client")
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Tag '{tag}' not found in {self._client_type} client"
            )
            
        value = self._tag_values[tag]
        logger.debug(f"Read mock {self._client_type} tag {tag} = {value}")
        return value

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write mock tag value.
        
        Args:
            tag: Tag name to write
            value: Value to write
            
        Raises:
            HTTPException: If write fails or tag not found
        """
        # Check connection
        if not self._connected:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Mock {self._client_type} client not connected"
            )
            
        # Simulate write delay and possible error
        await self._simulate_delay("write")
        self._simulate_error("write")
        
        # Set tag value
        if tag not in self._tag_values:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Tag '{tag}' not found in {self._client_type} client"
            )
            
        self._tag_values[tag] = value
        logger.debug(f"Wrote mock {self._client_type} tag {tag} = {value}")

    async def read_tags(self, tags: Dict[str, Any]) -> Dict[str, Any]:
        """Read multiple mock tag values.
        
        Args:
            tags: Dict of tag names to read
            
        Returns:
            Dict of tag values
            
        Raises:
            HTTPException: If read fails or tag not found
        """
        # Check connection
        if not self._connected:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Mock {self._client_type} client not connected"
            )
            
        # Simulate read delay and possible error
        await self._simulate_delay("read")
        self._simulate_error("read")
        
        # Get tag values
        values = {}
        for tag in tags:
            if tag not in self._tag_values:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Tag '{tag}' not found in {self._client_type} client"
                )
            values[tag] = self._tag_values[tag]
            
        logger.debug(f"Read {len(values)} mock {self._client_type} tags")
        return values

    async def write_tags(self, tags: Dict[str, Any]) -> None:
        """Write multiple mock tag values.
        
        Args:
            tags: Dictionary of tag names and values
            
        Raises:
            HTTPException: If write fails or any tag not found
        """
        for tag, value in tags.items():
            await self.write_tag(tag, value)

    async def start(self) -> None:
        """Start the mock client.
        
        This establishes the initial connection.
        
        Raises:
            HTTPException: If startup fails
        """
        await self.connect()
        logger.info(f"Started mock {self._client_type} client")

    async def stop(self) -> None:
        """Stop the mock client.
        
        This disconnects from the simulated hardware.
        
        Raises:
            HTTPException: If stop fails
        """
        await self.disconnect()
        logger.info(f"Stopped mock {self._client_type} client")

    async def check_connection(self) -> bool:
        """Check if mock client is connected.
        
        Returns:
            True if connected, False otherwise
            
        Raises:
            HTTPException: If connection check fails
        """
        # Simulate connection check delay and possible error
        await self._simulate_delay("connect")
        self._simulate_error("connect")
        
        # Return connection status
        logger.debug(f"Mock {self._client_type} client connection status: {self._connected}")
        return self._connected

    async def get(self) -> Dict[str, Any]:
        """Get all tag values.
        
        Returns:
            Dict of all tag values
            
        Raises:
            HTTPException: If read fails
        """
        # Check connection
        if not self._connected:
            logger.error(f"Mock {self._client_type} client not connected")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Mock {self._client_type} client not connected"
            )
            
        # Simulate read delay and possible error
        await self._simulate_delay("read")
        self._simulate_error("read")
        
        # Return all tag values
        logger.debug(f"Reading all mock {self._client_type} tags ({len(self._tag_values)} tags)")
        values = self._tag_values.copy()  # Return copy to prevent modification
        logger.debug(f"Read {len(values)} mock {self._client_type} tags")
        return values
