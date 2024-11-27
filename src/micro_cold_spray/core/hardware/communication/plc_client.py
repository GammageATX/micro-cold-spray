"""PLC communication client using Productivity PLC library."""
from typing import Dict, Any
from loguru import logger
from pathlib import Path
import asyncio

from productivity import ProductivityPLC

from ...exceptions import HardwareConnectionError

class PLCClient:
    """Client for PLC communication using Productivity library."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize PLC client with configuration."""
        plc_config = config.get('hardware', {}).get('network', {}).get('plc', {})
        self._address = plc_config.get('address')
        self._tag_file = Path(plc_config.get('tag_file'))
        self._plc = ProductivityPLC(self._address, str(self._tag_file))
        
        logger.info(f"PLCClient initialized with address={self._address}")

    async def get_all_tags(self) -> Dict[str, Any]:
        """Get all tag values from PLC using CSV definitions."""
        try:
            return await self._plc.read_all_tags()
        except asyncio.CancelledError:
            # Suppress cancelled connection attempts
            logger.debug("PLC connection attempt cancelled")
            return {}
        except Exception as e:
            logger.error(f"Failed to read tags: {e}")
            raise HardwareConnectionError("Failed to read tags") from e

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Write single tag value to PLC."""
        try:
            await self._plc.write_tag(tag_name, value)
        except Exception as e:
            logger.error(f"Failed to write tag {tag_name}: {e}")
            raise HardwareConnectionError(f"Failed to write tag {tag_name}") from e