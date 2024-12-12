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
        logger.info("MockPLCClient initialized")

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
        return self._tag_values.get(tag, 0.0)  # Default to 0.0 for unknown tags

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write mock tag value."""
        await asyncio.sleep(0.05)  # Simulate write delay
        self._tag_values[tag] = value
        logger.debug(f"MockPLCClient wrote {tag}={value}")


class MockSSHClient(CommunicationClient):
    """Mock SSH client for testing."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize mock SSH client."""
        super().__init__("mock_ssh", config)
        self._tag_values: Dict[str, Any] = {}
        logger.info("MockSSHClient initialized")

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
        return self._tag_values.get(tag, 0.0)  # Default to 0.0 for unknown tags

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write mock tag value."""
        await asyncio.sleep(0.05)  # Simulate write delay
        self._tag_values[tag] = value
        logger.debug(f"MockSSHClient wrote {tag}={value}")
