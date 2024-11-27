from typing import Dict, Any
from loguru import logger
import paramiko
import asyncio

from ...exceptions import HardwareConnectionError

class SSHClient:
    """Client for SSH communication with motion controller."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize SSH client with configuration."""
        ssh_config = config.get('hardware', {}).get('network', {}).get('ssh', {})
        self._host = ssh_config.get('host')
        self._port = ssh_config.get('port', 22)
        self._username = ssh_config.get('username')
        self._password = ssh_config.get('password')
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        logger.info(f"SSHClient initialized for {self._username}@{self._host}")

    async def connect(self) -> None:
        """Connect to motion controller and wait for welcome message."""
        try:
            self._client.connect(
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password
            )
            # Wait for system to be ready
            await asyncio.sleep(5)  # Simple delay for system initialization
            logger.info("Connected to motion controller")
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise HardwareConnectionError("Failed to connect to motion controller") from e

    async def disconnect(self) -> None:
        """Disconnect from motion controller."""
        try:
            self._client.close()
            logger.info("Disconnected from motion controller")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            raise HardwareConnectionError("Failed to disconnect from motion controller") from e

    async def write_command(self, command: str) -> None:
        """Write command to motion controller."""
        try:
            self._client.exec_command(command)
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            raise HardwareConnectionError(f"Failed to send command: {str(e)}") from e
