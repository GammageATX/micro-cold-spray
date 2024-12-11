"""PLC communication client using Productivity PLC library."""

import asyncio
from pathlib import Path
from typing import Any, Dict

from loguru import logger
from productivity import ProductivityPLC

from ..exceptions import HardwareError
from .base import CommunicationClient


class PLCClient(CommunicationClient):
    """Client for PLC communication using Productivity library."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize PLC client with configuration."""
        super().__init__("plc", config)
        try:
            plc_config = config['hardware']['network']['plc']
            self._address = plc_config['ip']
            self._tag_file = Path(plc_config['tag_file'])

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
            f"PLCClient initialized with address={self._address}, tag_file={self._tag_file}"
        )

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

    async def read_tag(self, tag: str) -> Any:
        """Read tag value from PLC."""
        try:
            values = await self._plc.get()  # Library expects no arguments
            if tag not in values:
                raise KeyError(f"Tag {tag} not found in PLC response")
            return values[tag]
        except asyncio.CancelledError:
            logger.debug("PLC connection attempt cancelled")
            return None
        except Exception as e:
            logger.error(f"Failed to read tag {tag}: {e}")
            raise HardwareError(
                f"Failed to read tag {tag}",
                "plc",
                {"tag": tag, "error": str(e)}
            )

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write single tag value to PLC."""
        try:
            await self._plc.set({tag: value})  # Library expects a dict
        except Exception as e:
            logger.error(f"Failed to write tag {tag}: {e}")
            raise HardwareError(
                f"Failed to write tag {tag}",
                "plc",
                {
                    "tag": tag,
                    "value": value,
                    "error": str(e)
                }
            )
