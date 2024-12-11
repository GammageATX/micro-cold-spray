"""SSH client for feeder controller communication."""

from typing import Any, Dict, Optional
from loguru import logger
import paramiko

from .. import HardwareError


class SSHClient:
    """Client for communicating with feeder controller via SSH."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize SSH client with configuration."""
        try:
            ssh_config = config['hardware']['network']['ssh']
            self._host = ssh_config.get('host')
            self._username = ssh_config.get('username')
            self._password = ssh_config.get('password')
            self._port = ssh_config.get('port', 22)
            self._timeout = ssh_config.get('timeout', 5)
            self._connected = False
            self._client: Optional[paramiko.SSHClient] = None

            if not all([self._host, self._username, self._password]):
                raise HardwareError(
                    "Missing required SSH configuration",
                    "feeder",
                    {"config": ssh_config}
                )

        except KeyError as e:
            raise HardwareError(
                f"Missing required SSH configuration: {e}",
                "feeder",
                {"config": config}
            )
        except Exception as e:
            raise HardwareError(
                "Failed to initialize SSH client",
                "feeder",
                {"error": str(e)}
            )

        logger.info(f"SSHClient initialized for {self._host}")

    async def test_connection(self) -> bool:
        """Test if feeder controller is reachable."""
        try:
            transport = paramiko.Transport((self._host, self._port))
            transport.connect(
                username=self._username,
                password=self._password,
                timeout=self._timeout
            )
            transport.close()
            return True
        except Exception as e:
            logger.error(f"SSH connection test failed: {e}")
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
                        "port": self._port
                    }
                )

            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                timeout=self._timeout
            )
            self._connected = True
            logger.info("Connected to feeder controller")

        except paramiko.AuthenticationException:
            self._connected = False
            logger.error("SSH authentication failed")
            raise HardwareError(
                "Failed to connect to feeder controller",
                "feeder",
                {
                    "error": "Authentication failed",
                    "host": self._host
                }
            )
        except Exception as e:
            self._connected = False
            logger.error(f"SSH connection failed: {e}")
            raise HardwareError(
                "Failed to connect to feeder controller",
                "feeder",
                {
                    "error": str(e),
                    "host": self._host
                }
            )

    async def disconnect(self) -> None:
        """Disconnect from feeder controller."""
        try:
            if self._client:
                self._client.close()
            self._connected = False
            logger.info("Disconnected from feeder controller")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            raise HardwareError(
                "Failed to disconnect from feeder controller",
                "feeder",
                {
                    "error": str(e),
                    "host": self._host
                }
            )

    async def write_command(self, command: str) -> None:
        """Write command to feeder controller."""
        try:
            if not self._connected:
                if not await self.test_connection():
                    raise HardwareError(
                        "Cannot send command - feeder controller not connected",
                        "feeder",
                        {
                            "host": self._host,
                            "command": command
                        }
                    )
            self._client.exec_command(command)
            logger.debug(f"Sent command: {command}")
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            raise HardwareError(
                f"Failed to send command: {str(e)}",
                "feeder",
                {
                    "command": command,
                    "error": str(e)
                }
            )
