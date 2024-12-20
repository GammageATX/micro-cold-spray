"""SSH communication client for remote hardware control."""

import asyncssh
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
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
            
            # Handle authentication
            self._key_file = Path(ssh_config.get('key_file', '')) if 'key_file' in ssh_config else None
            self._password = ssh_config.get('password')
            
            # Validate we have either key file or password
            if (not self._key_file or not self._key_file.exists()) and not self._password:
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message="No valid authentication method provided",
                    context={"host": self._host}
                )

        except KeyError as e:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Missing required SSH config field: {e}",
                context={"field": str(e)}
            )
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to initialize SSH client: {e}",
                context={"error": str(e)},
                cause=e
            )

        self._connection: Optional[asyncssh.SSHClientConnection] = None
        logger.info(f"SSHClient initialized for {self._username}@{self._host}")

    async def connect(self) -> None:
        """Establish SSH connection.
        
        Raises:
            HTTPException: If connection fails
        """
        try:
            # Setup connection options
            options = {
                'username': self._username,
                'port': self._port,
                'known_hosts': None  # Don't verify host keys for now
            }
            
            # Add authentication
            if self._key_file and self._key_file.exists():
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
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"host": self._host},
                cause=e
            )

    async def disconnect(self) -> None:
        """Close SSH connection.
        
        Raises:
            HTTPException: If disconnect fails
        """
        try:
            if self._connection:
                self._connection.close()  # Synchronous call
                await self._connection.wait_closed()  # Wait for close to complete
            self._connected = False
            logger.info(f"Disconnected from {self._host}")
        except Exception as e:
            error_msg = f"Error disconnecting from {self._host}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg,
                context={"host": self._host},
                cause=e
            )

    async def read_tag(self, tag: str) -> Any:
        """Read tag value via SSH command.
        
        Args:
            tag: Tag to read
            
        Returns:
            Tag value
            
        Raises:
            HTTPException: If read fails
        """
        if not self._connection:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Not connected",
                context={"host": self._host}
            )
            
        try:
            # Execute read command
            command = f"read_tag {tag}"  # Replace with actual command
            result = await self._connection.run(command)
            
            if result.exit_status != 0:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Failed to read tag: {result.stderr}",
                    context={
                        "tag": tag,
                        "exit_status": result.exit_status
                    }
                )
                
            # Parse result
            return float(result.stdout.strip())  # Adjust parsing as needed
            
        except Exception as e:
            error_msg = f"Failed to read tag {tag}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={"tag": tag},
                cause=e
            )

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write tag value via SSH command.
        
        Args:
            tag: Tag to write
            value: Value to write
            
        Raises:
            HTTPException: If write fails
        """
        if not self._connection:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Not connected",
                context={"host": self._host}
            )
            
        try:
            # Execute write command
            command = f"write_tag {tag} {value}"  # Replace with actual command
            result = await self._connection.run(command)
            
            if result.exit_status != 0:
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message=f"Failed to write tag: {result.stderr}",
                    context={
                        "tag": tag,
                        "value": value,
                        "exit_status": result.exit_status
                    }
                )
                
        except Exception as e:
            error_msg = f"Failed to write tag {tag}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg,
                context={
                    "tag": tag,
                    "value": value
                },
                cause=e
            )
