from typing import Dict, Any
from loguru import logger
import paramiko
import asyncio
from datetime import datetime
import platform
import subprocess

from ...exceptions import HardwareError

class SSHClient:
    """Client for SSH communication with feeder controllers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize SSH client with configuration."""
        try:
            ssh_config = config.get('hardware', {}).get('network', {}).get('ssh', {})
            self._host = ssh_config.get('host')
            self._port = ssh_config.get('port', 22)
            self._username = ssh_config.get('username')
            self._password = ssh_config.get('password')
            self._connected = False
            
            if not all([self._host, self._username, self._password]):
                raise HardwareError(
                    "Missing required SSH configuration",
                    "feeder",
                    {"config": ssh_config}
                )
            
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logger.info(f"SSHClient initialized for {self._username}@{self._host}")
            
        except Exception as e:
            raise HardwareError(
                "Failed to initialize SSH client",
                "feeder",
                {"error": str(e)}
            )

    async def test_connection(self) -> bool:
        """Test if feeder controller is reachable and establish connection if possible."""
        try:
            # Platform specific ping command
            if platform.system().lower() == "windows":
                ping_cmd = ["ping", "-n", "1", "-w", "1000", self._host]
            else:
                ping_cmd = ["ping", "-c", "1", "-W", "1", self._host]
            
            # Run ping command
            process = await asyncio.create_subprocess_exec(
                *ping_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            await process.communicate()
            is_reachable = process.returncode == 0
            
            if is_reachable:
                logger.debug(f"Feeder controller at {self._host} is reachable")
                # If reachable, try to establish SSH connection
                try:
                    self._client.connect(
                        hostname=self._host,
                        port=self._port,
                        username=self._username,
                        password=self._password,
                        timeout=5  # Add timeout to prevent hanging
                    )
                    self._connected = True
                    logger.info(f"SSH connection established to {self._host}")
                except Exception as ssh_error:
                    logger.error(f"SSH connection failed: {ssh_error}")
                    self._connected = False
            else:
                logger.warning(f"Feeder controller at {self._host} is not reachable")
                self._connected = False
            
            return self._connected
            
        except Exception as e:
            logger.error(f"Error testing feeder controller connection: {e}")
            self._connected = False
            return False

    async def connect(self) -> None:
        """Connect to feeder controller."""
        try:
            if not await self.test_connection():
                raise HardwareError(
                    "Feeder controller not reachable",
                    "feeder",
                    {
                        "host": self._host,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
            self._client.connect(
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password
            )
            self._connected = True
            logger.info("Connected to feeder controller")
            
        except Exception as e:
            self._connected = False
            logger.error(f"SSH connection failed: {e}")
            raise HardwareError(
                "Failed to connect to feeder controller",
                "feeder",
                {
                    "host": self._host,
                    "port": self._port,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def disconnect(self) -> None:
        """Disconnect from feeder controller."""
        try:
            self._client.close()
            self._connected = False
            logger.info("Disconnected from feeder controller")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            raise HardwareError(
                "Failed to disconnect from feeder controller",
                "feeder",
                {
                    "host": self._host,
                    "port": self._port,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def write_command(self, command: str) -> None:
        """Write command to feeder controller."""
        try:
            if not self._connected:
                if not await self.test_connection():
                    raise HardwareError(
                        "Cannot send command - feeder controller not connected",
                        "feeder"
                    )
            self._client.exec_command(command)
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            raise HardwareError(
                f"Failed to send command: {str(e)}",
                "feeder",
                {
                    "host": self._host,
                    "port": self._port,
                    "command": command,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )
