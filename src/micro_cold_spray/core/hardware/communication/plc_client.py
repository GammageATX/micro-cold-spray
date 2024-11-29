"""PLC communication client using Productivity PLC library."""
from typing import Dict, Any
from loguru import logger
from pathlib import Path
import asyncio
from datetime import datetime
import platform
import subprocess

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
        logger.info(f"PLCClient initialized with address={self._address}, tag_file={self._tag_file}")

    async def test_connection(self) -> bool:
        """Test if PLC is reachable without attempting full connection."""
        try:
            # Platform specific ping command
            if platform.system().lower() == "windows":
                ping_cmd = ["ping", "-n", "1", "-w", "1000", self._address]
            else:
                ping_cmd = ["ping", "-c", "1", "-W", "1", self._address]
            
            # Run ping command
            process = await asyncio.create_subprocess_exec(
                *ping_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            await process.communicate()
            self._connected = process.returncode == 0
            
            if self._connected:
                logger.debug(f"PLC at {self._address} is reachable")
            else:
                logger.warning(f"PLC at {self._address} is not reachable")
            
            return self._connected
            
        except Exception as e:
            logger.error(f"Error testing PLC connection: {e}")
            self._connected = False
            return False

    async def get_all_tags(self) -> Dict[str, Any]:
        """Get all tag values from PLC using CSV definitions."""
        try:
            if not self._connected:
                if not await self.test_connection():
                    return {}  # Return empty dict if not connected
            return await self._plc.read_all_tags()
        except asyncio.CancelledError:
            logger.debug("PLC connection attempt cancelled")
            return {}
        except Exception as e:
            logger.error(f"Failed to read tags: {e}")
            raise HardwareError("Failed to read tags", "plc") from e

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Write single tag value to PLC."""
        try:
            if not self._connected:
                if not await self.test_connection():
                    raise HardwareError("Cannot write tag - PLC not connected", "plc")
            await self._plc.write_tag(tag_name, value)
        except Exception as e:
            logger.error(f"Failed to write tag {tag_name}: {e}")
            raise HardwareError(f"Failed to write tag {tag_name}", "plc") from e

    async def connect(self) -> None:
        """Connect to PLC."""
        try:
            if not self._connected:
                raise HardwareError("PLC not reachable", "plc", {
                    "ip": self._address,
                    "timestamp": datetime.now().isoformat()
                })
            
            await self._plc.connect()
            
        except Exception as e:
            logger.error(f"PLC connection failed: {e}")
            self._connected = False
            raise HardwareError("Failed to connect to PLC", "plc", {
                "ip": self._address,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def disconnect(self) -> None:
        """Disconnect from PLC."""
        try:
            if hasattr(self._plc, 'disconnect'):
                await self._plc.disconnect()
            self._connected = False
        except Exception as e:
            logger.error(f"Error disconnecting from PLC: {e}")
            raise HardwareError("Failed to disconnect from PLC", "plc", {
                "ip": self._address,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })