"""PLC communication client."""

import logging
from typing import Any, Dict, Optional
from fastapi import status
from loguru import logger
from productivity import ProductivityPLC
from pymodbus.pdu import ExceptionResponse

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.clients.base import CommunicationClient


class PLCClient(CommunicationClient):
    """Client for communicating with Productivity PLC."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize PLC client.
        
        Args:
            config: Client configuration from communication.yaml
        """
        super().__init__(config)
        
        # Extract PLC config
        plc_config = config["network"]["plc"]
        self._ip = plc_config["ip"]
        self._tag_file = plc_config["tag_file"]
        self._timeout = plc_config.get("timeout", 5.0)
        self._plc: Optional[ProductivityPLC] = None
        self._tags: Dict[str, Any] = {}
        logger.info(f"Initialized PLC client for {self._ip}")

    async def connect(self) -> None:
        """Connect to PLC.
        
        Connection is established on first request.
        
        Raises:
            HTTPException: If connection fails
        """
        try:
            # Create PLC instance
            self._plc = ProductivityPLC(self._ip, self._tag_file, self._timeout)
            
            # Get tag configuration and test connection with first request
            self._tags = self._plc.get_tags()
            await self._plc.get()
            
            self._connected = True
            logger.info(f"Connected to PLC at {self._ip} with {len(self._tags)} tags")
            
        except Exception as e:
            error_msg = f"Failed to connect to PLC at {self._ip}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def disconnect(self) -> None:
        """Disconnect from PLC.
        
        Connection is closed automatically when requests stop.
        """
        self._plc = None
        self._connected = False
        logger.info(f"Disconnected from PLC at {self._ip}")

    async def read_tag(self, tag: str) -> Any:
        """Read tag value.
        
        Args:
            tag: Tag name to read
            
        Returns:
            Tag value
            
        Raises:
            HTTPException: If read fails
        """
        if not self._plc:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"PLC not connected at {self._ip}"
            )
            
        if tag not in self._tags:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Tag '{tag}' not found in PLC"
            )
            
        try:
            values = await self._plc.get()
            if tag not in values:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Tag '{tag}' not found in PLC response"
                )
                
            # Check for Modbus exceptions
            if isinstance(values, ExceptionResponse):
                error_msg = f"Modbus exception reading tag '{tag}' from PLC: {values}"
                logger.error(error_msg)
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=error_msg
                )
                
            return values[tag]
            
        except Exception as e:
            error_msg = f"Failed to read tag '{tag}' from PLC: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def write_tag(self, tag: str, value: Any) -> None:
        """Write tag value.
        
        Args:
            tag: Tag name to write
            value: Value to write
            
        Raises:
            HTTPException: If write fails
        """
        if not self._plc:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"PLC not connected at {self._ip}"
            )
            
        if tag not in self._tags:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Tag '{tag}' not found in PLC"
            )
            
        try:
            # The library handles type validation and conversion
            responses = await self._plc.set({tag: value})
            
            # Check for Modbus exceptions
            if any("error" in str(r).lower() for r in responses):
                error_msg = f"Modbus error writing tag '{tag}' = {value} to PLC: {responses}"
                logger.error(error_msg)
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=error_msg
                )
                
            logger.debug(f"Wrote tag {tag} = {value}")
            
        except Exception as e:
            error_msg = f"Failed to write tag '{tag}' = {value} to PLC: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )
