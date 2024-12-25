"""Mock client that simulates PLC behavior."""

import asyncio
import yaml
from typing import Any, Dict, Optional, List
from pathlib import Path
from loguru import logger


class MockPLCClient:
    """Mock client that simulates PLC behavior."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize mock client.
        
        Args:
            config: Client configuration
        """
        self._connected = False
        self._config = config
        
        # Load mock data
        mock_data_path = Path("config/mock_data.yaml")
        if not mock_data_path.exists():
            logger.warning(f"Mock data file not found: {mock_data_path}")
            self._mock_data = {"plc_tags": {}}
        else:
            with open(mock_data_path) as f:
                self._mock_data = yaml.safe_load(f)
            logger.info(f"Loaded mock data from {mock_data_path}")
            
        # Initialize mock tag values
        self._plc_tags = self._mock_data.get("plc_tags", {})
        
        # Add simulated behavior
        self._update_task = None
        self._running = False
        logger.info(f"Mock client initialized with {len(self._plc_tags)} tags")

    async def connect(self) -> None:
        """Simulate connection."""
        await asyncio.sleep(0.1)  # Simulate connection delay
        self._connected = True
        self._running = True
        
        # Start background task to simulate tag updates
        self._update_task = asyncio.create_task(self._simulate_updates())
        logger.info("Mock client connected")

    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None
            
        self._connected = False
        logger.info("Mock client disconnected")

    async def read_tag(self, tag: str) -> Any:
        """Read mock tag value.
        
        Args:
            tag: Tag name to read
            
        Returns:
            Mock tag value
        """
        if not self._connected:
            raise ConnectionError("Mock client not connected")
            
        # Return mock value if exists, otherwise 0
        value = self._plc_tags.get(tag, 0)
        logger.debug(f"Read mock tag {tag} = {value}")
        return value

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write mock tag value.
        
        Args:
            tag: Tag name to write
            value: Value to write
        """
        if not self._connected:
            raise ConnectionError("Mock client not connected")
            
        # Update mock value
        self._plc_tags[tag] = value
        logger.debug(f"Wrote mock tag {tag} = {value}")

    def is_connected(self) -> bool:
        """Check if mock client is connected.
        
        Returns:
            Connection status
        """
        return self._connected

    async def get(self, tags: List[str]) -> Dict[str, Any]:
        """Read multiple mock tag values.
        
        Args:
            tags: List of tag names to read
            
        Returns:
            Dictionary mapping tag names to values
        """
        if not self._connected:
            raise ConnectionError("Mock client not connected")
            
        # Return mock values for all requested tags
        values = {tag: self._plc_tags.get(tag, 0) for tag in tags}
        logger.debug(f"Read mock tags: {values}")
        return values

    async def _simulate_updates(self) -> None:
        """Background task to simulate tag value updates."""
        try:
            while self._running:
                # Simulate some tag value changes
                for tag in self._plc_tags:
                    if "Position" in tag:
                        # Simulate small position changes
                        current = self._plc_tags[tag]
                        self._plc_tags[tag] = current + (0.1 if current < 100 else -0.1)
                    elif "Pressure" in tag:
                        # Simulate pressure fluctuations
                        current = self._plc_tags[tag]
                        self._plc_tags[tag] = current + (0.05 if current < 5 else -0.05)
                        
                await asyncio.sleep(0.1)  # Update every 100ms
                
        except asyncio.CancelledError:
            logger.debug("Mock update simulation stopped")
            raise
        except Exception as e:
            logger.error(f"Error in mock update simulation: {str(e)}")
            raise
