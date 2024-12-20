"""Mock client for testing without hardware."""

import asyncio
import random
from typing import Any, Dict
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.clients.base import CommunicationClient


class MockClient(CommunicationClient):
    """Mock client that simulates hardware communication."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize mock client."""
        super().__init__("mock", config)
        self._tags = {}
        self._delay = config.get("delay", 0.1)  # Simulated communication delay
        self._error_rate = config.get("error_rate", 0.0)  # Probability of errors
        logger.info(f"Initialized mock client with delay={self._delay}s")

    async def connect(self) -> None:
        """Simulate connecting to hardware."""
        try:
            await asyncio.sleep(self._delay)
            if random.random() < self._error_rate:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Simulated connection error",
                    context={"error_rate": self._error_rate}
                )
            self._connected = True
            logger.debug("Mock client connected")
        except Exception as e:
            logger.error(f"Failed to connect mock client: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to connect mock client: {e}",
                context={"error": str(e)},
                cause=e
            )

    async def disconnect(self) -> None:
        """Simulate disconnecting from hardware."""
        try:
            await asyncio.sleep(self._delay)
            if random.random() < self._error_rate:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Simulated disconnect error",
                    context={"error_rate": self._error_rate}
                )
            self._connected = False
            logger.debug("Mock client disconnected")
        except Exception as e:
            logger.error(f"Failed to disconnect mock client: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to disconnect mock client: {e}",
                context={"error": str(e)},
                cause=e
            )

    async def read_tag(self, tag: str) -> Any:
        """Read simulated tag value."""
        try:
            await asyncio.sleep(self._delay)
            if random.random() < self._error_rate:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Simulated read error",
                    context={"tag": tag, "error_rate": self._error_rate}
                )
            if tag not in self._tags:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Tag {tag} not found",
                    context={"tag": tag}
                )
            return self._tags[tag]
        except Exception as e:
            logger.error(f"Failed to read tag {tag}: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to read tag {tag}",
                context={"tag": tag, "error": str(e)},
                cause=e
            )

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write simulated tag value."""
        try:
            await asyncio.sleep(self._delay)
            if random.random() < self._error_rate:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Simulated write error",
                    context={
                        "tag": tag,
                        "value": value,
                        "error_rate": self._error_rate
                    }
                )
            self._tags[tag] = value
            logger.debug(f"Wrote tag {tag}={value}")
        except Exception as e:
            logger.error(f"Failed to write tag {tag}: {e}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to write tag {tag}",
                context={
                    "tag": tag,
                    "value": value,
                    "error": str(e)
                },
                cause=e
            )
