"""PLC communication client using Productivity PLC library."""
import asyncio
from pathlib import Path
from typing import Any, Dict

from loguru import logger
from productivity import ProductivityPLC

from ...exceptions import HardwareError


class PLCClient:
    """Client for PLC communication using Productivity library."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize PLC client with configuration."""
        try:
            plc_config = config['hardware']['network']['plc']
            self._address = plc_config['address']
            self._tag_file = Path(plc_config['tag_file'])
            self._connected = False

            # Validate tag file exists
            if not self._tag_file.exists():
                raise HardwareError(
                    f"PLC tag file not found: {self._tag_file}",
                    "plc",
                    {"tag_file": str(self._tag_file)}
                )

        except KeyError as e:
            raise HardwareError(
                f"Missing required PLC configuration: {e}",
                "plc",
                {"config": config}
            )
        except Exception as e:
            raise HardwareError(
                f"Failed to initialize PLC client: {e}",
                "plc",
                {"address": self._address}
            )

        self._plc = ProductivityPLC(self._address, str(self._tag_file))
        logger.info(
            f"PLCClient initialized with address={
                self._address}, tag_file={
                self._tag_file}")

    async def connect(self) -> None:
        """Connect to PLC.

        For the real PLC client, this is a no-op since the ProductivityPLC library
        handles connections automatically per-request.
        """
        self._connected = True
        logger.debug("PLCClient ready")

    async def disconnect(self) -> None:
        """Disconnect from PLC.

        For the real PLC client, this is a no-op since the ProductivityPLC library
        handles connections automatically per-request.
        """
        self._connected = False
        logger.debug("PLCClient disconnected")

    async def get_all_tags(self) -> Dict[str, Any]:
        """Get all tag values from PLC using CSV definitions."""
        try:
            return await self._plc.get()  # Library expects no arguments
        except asyncio.CancelledError:
            logger.debug("PLC connection attempt cancelled")
            return {}
        except Exception as e:
            logger.error(f"Failed to read tags: {e}")
            raise HardwareError("Failed to read tags", "plc") from e

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Write single tag value to PLC."""
        try:
            await self._plc.set({tag_name: value})  # Library expects a dict
        except Exception as e:
            logger.error(f"Failed to write tag {tag_name}: {e}")
            raise HardwareError(f"Failed to write tag {tag_name}", "plc") from e
