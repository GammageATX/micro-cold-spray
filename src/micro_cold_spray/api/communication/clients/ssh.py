"""SSH communication client for remote hardware control."""

import asyncssh
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from ..exceptions import HardwareError, ConnectionError
from .base import CommunicationClient


class SSHClient(CommunicationClient):
    """Client for SSH-based hardware communication."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize SSH client with configuration."""
        super().__init__("ssh", config)
        try:
            # Config is already at SSH level
            ssh_config = config
            self._host = ssh_config['host']
            self._port = ssh_config.get('port', 22)
            self._username = ssh_config['username']
            self._key_file = Path(ssh_config.get('key_file', ''))
            self._password = ssh_config.get('password')
            
            # Validate we have either key file or password
            if not self._key_file.exists() and not self._password:
                raise HardwareError(
                    "No valid authentication method provided",
                    "ssh",
                    {"host": self._host}
                )

        except KeyError as e:
            raise ValueError(f"Missing required SSH config field: {e}")
        except Exception as e:
            raise ValueError(f"Failed to initialize SSH client: {e}")

        self._connection: Optional[asyncssh.SSHClientConnection] = None
        logger.info(f"SSHClient initialized for {self._username}@{self._host}")

    async def connect(self) -> None:
        """Establish SSH connection.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Setup connection options
            options = {
                'username': self._username,
                'port': self._port,
                'known_hosts': None  # Don't verify host keys for now
            }
            
            # Add authentication
            if self._key_file.exists():
                options['client_keys'] = [str(self._key_file)]
            elif self._password:
                options['password'] = self._password
                
            # Connect
            self._connection = await asyncssh.connect(self._host, **options)
            self._connected = True
            logger.info(f"Connected to {self._host}")
            
        except Exception as e:
            error_msg = f"Failed to connect to {self._host}: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg, {"host": self._host})

    async def disconnect(self) -> None:
        """Close SSH connection.
        
        Raises:
            ConnectionError: If disconnect fails
        """
        try:
            if self._connection:
                self._connection.close()
                await self._connection.wait_closed()
            self._connected = False
            logger.info(f"Disconnected from {self._host}")
        except Exception as e:
            error_msg = f"Error disconnecting from {self._host}: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg, {"host": self._host})

    async def read_tag(self, tag: str) -> Any:
        """Read tag value via SSH command.
        
        Args:
            tag: Tag to read
            
        Returns:
            Tag value
            
        Raises:
            ConnectionError: If read fails
        """
        if not self._connection:
            raise ConnectionError("Not connected", {"host": self._host})
            
        try:
            # Execute read command
            command = f"read_tag {tag}"  # Replace with actual command
            result = await self._connection.run(command)
            
            if result.exit_status != 0:
                raise ConnectionError(
                    f"Failed to read tag: {result.stderr}",
                    {
                        "tag": tag,
                        "exit_status": result.exit_status
                    }
                )
                
            # Parse result
            return float(result.stdout.strip())  # Adjust parsing as needed
            
        except Exception as e:
            error_msg = f"Failed to read tag {tag}: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg, {"tag": tag})

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write tag value via SSH command.
        
        Args:
            tag: Tag to write
            value: Value to write
            
        Raises:
            ConnectionError: If write fails
        """
        if not self._connection:
            raise ConnectionError("Not connected", {"host": self._host})
            
        try:
            # Execute write command
            command = f"write_tag {tag} {value}"  # Replace with actual command
            result = await self._connection.run(command)
            
            if result.exit_status != 0:
                raise ConnectionError(
                    f"Failed to write tag: {result.stderr}",
                    {
                        "tag": tag,
                        "value": value,
                        "exit_status": result.exit_status
                    }
                )
                
        except Exception as e:
            error_msg = f"Failed to write tag {tag}: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(
                error_msg,
                {
                    "tag": tag,
                    "value": value
                }
            )
