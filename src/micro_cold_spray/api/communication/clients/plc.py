"""PLC communication client using Productivity PLC library."""

import asyncio
from pathlib import Path
from typing import Any, Dict

from loguru import logger
from productivity import ProductivityPLC

from ...base.exceptions import ServiceError, ValidationError
from .base import CommunicationClient


class PLCClient(CommunicationClient):
    """Client for PLC communication."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize PLC client."""
        super().__init__("plc", config)
        try:
            # Extract required configuration
            self._ip = config['ip']
            self._tag_file = Path(config['tag_file'])
            self._polling_interval = config['polling_interval']
            self._retry_delay = config.get('retry', {}).get('delay', 1.0)
            self._max_attempts = config.get('retry', {}).get('max_attempts', 3)
            self._timeout = config.get('timeout', 5.0)
            
            # Validate tag file exists
            if not self._tag_file.exists():
                raise ValidationError(
                    f"Tag file not found: {self._tag_file}",
                    {"path": str(self._tag_file)}
                )
            
            logger.info(f"Initialized PLC client for {self._ip}")
            
        except KeyError as e:
            raise ValidationError(
                f"Missing required PLC config field: {e}",
                {"field": str(e)}
            )
        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(
                f"Failed to initialize PLC client: {e}",
                {"error": str(e)}
            )

        self._plc = ProductivityPLC(self._ip, str(self._tag_file))
        logger.info(
            f"PLCClient initialized with address={self._ip}, tag_file={self._tag_file}"
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
                raise ValidationError(
                    f"Tag {tag} not found in PLC response",
                    {"tag": tag}
                )
            return values[tag]
        except asyncio.CancelledError:
            logger.debug("PLC connection attempt cancelled")
            return None
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to read tag {tag}: {e}")
            raise ServiceError(
                f"Failed to read tag {tag}",
                {"tag": tag, "error": str(e)}
            )

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write single tag value to PLC."""
        try:
            await self._plc.set({tag: value})  # Library expects a dict
        except Exception as e:
            logger.error(f"Failed to write tag {tag}: {e}")
            raise ServiceError(
                f"Failed to write tag {tag}",
                {
                    "tag": tag,
                    "value": value,
                    "error": str(e)
                }
            )
