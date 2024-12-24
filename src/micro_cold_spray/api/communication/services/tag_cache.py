"""Tag cache service implementation."""

from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
from fastapi import status
from loguru import logger
from pydantic import BaseModel

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService
from micro_cold_spray.api.communication.clients.factory import create_client


class TagValue(BaseModel):
    """Internal model for tag value."""
    name: str
    value: Any
    timestamp: float
    is_internal: bool = False  # Whether this is an internally tracked value vs PLC tag


class TagCacheService:
    """Service for caching and accessing tag values."""

    def __init__(
        self,
        plc_address: str,
        tags_file: str,
        tag_mapping: TagMappingService,
        poll_rate: float = 0.1,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize tag cache service.
        
        Args:
            plc_address: PLC IP address
            tags_file: Path to CSV file containing tag definitions
            tag_mapping: Service for mapping between internal and PLC tag names
            poll_rate: How often to poll tags in seconds (default 100ms)
            config: Optional service configuration
        """
        self._service_name = "tag_cache"
        self._version = "1.0.0"
        self._config = config or {}
        
        # Create PLC client based on force_mock setting
        client_type = "mock" if self._config.get("communication", {}).get("force_mock", False) else "plc"
        self._plc = create_client(client_type=client_type, config=self._config)
        
        self._tag_mapping = tag_mapping
        self._poll_rate = poll_rate
        self._cache: Dict[str, TagValue] = {}
        self._polling_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._start_time = None
        self._connection_errors = 0  # Track consecutive connection errors
        self._max_connection_errors = 3  # Stop service after this many consecutive errors
        logger.info("TagCacheService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def initialize(self) -> None:
        """Initialize tag cache service.
        
        Raises:
            HTTPException: If initialization fails
        """
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Reset error count
            self._connection_errors = 0

            # Wait for tag mapping service to be ready
            if not self._tag_mapping.is_running:
                logger.error("Tag mapping service not running")
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Tag mapping service not running"
                )

            # Connect to PLC
            logger.info("Connecting to PLC...")
            await self._plc.connect()
            logger.info("Connected to PLC")

            # Start polling task
            logger.info("Starting polling task...")
            self._polling_task = asyncio.create_task(self._poll_tags())
            self._is_running = True
            logger.info("Tag cache service initialized")

        except Exception as e:
            error_msg = f"Failed to initialize tag cache service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start tag cache service.
        
        Raises:
            HTTPException: If startup fails
        """
        try:
            if not self.is_running:
                await self.initialize()

            self._start_time = datetime.now()
            logger.info("Tag cache service started")

        except Exception as e:
            error_msg = f"Failed to start tag cache service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop tag cache service."""
        try:
            if not self.is_running:
                return

            # Stop polling task
            if self._polling_task:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
                self._polling_task = None

            self._cache.clear()
            self._is_running = False
            self._start_time = None
            logger.info("Tag cache service stopped")

        except Exception as e:
            error_msg = f"Failed to stop tag cache service: {str(e)}"
            logger.error(error_msg)
            # Don't raise during shutdown

    async def _poll_tags(self) -> None:
        """Poll all PLC tags at specified rate."""
        while True:
            try:
                # Connect if needed
                if not self._plc.is_connected:
                    await self._plc.connect()

                # Get all tag values from PLC
                logger.debug("Polling PLC tags...")
                plc_values = await self._plc.get()
                now = datetime.now().timestamp()
                logger.debug(f"Got {len(plc_values)} tag values from PLC")

                # Map PLC tags to internal names and update cache
                for plc_name, value in plc_values.items():
                    # Get internal name for this PLC tag
                    internal_name = self._tag_mapping.get_internal_tag(plc_name)
                    logger.debug(f"Mapping {plc_name} -> {internal_name}")
                    if internal_name:  # Only cache if we have a mapping
                        self._cache[internal_name] = TagValue(
                            name=internal_name,
                            value=value,
                            timestamp=now,
                            is_internal=False
                        )
                        logger.debug(f"Updated tag cache: {internal_name} = {value}")

                # Reset error count on successful poll
                self._connection_errors = 0

            except Exception as e:
                logger.error(f"Failed to poll tags: {str(e)}")
                self._connection_errors += 1
                
                # Stop service if too many consecutive errors
                if self._connection_errors >= self._max_connection_errors:
                    logger.error(f"Too many consecutive connection errors ({self._connection_errors}), stopping service")
                    await self.stop()
                    return

            await asyncio.sleep(self._poll_rate)

    async def read_tag(self, name: str) -> Any:
        """Read tag value from cache.
        
        Args:
            name: Internal tag name
            
        Returns:
            Tag value
            
        Raises:
            HTTPException: If tag not found or service not running
        """
        try:
            if not self.is_running:
                logger.error("Tag cache service not running")
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            logger.debug(f"Reading tag: {name}")

            # Check if tag exists in mapping
            plc_tag = self._tag_mapping.get_plc_tag(name)
            logger.debug(f"Mapped {name} -> {plc_tag}")
            if not plc_tag:
                logger.error(f"Tag {name} not found in mapping")
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Tag {name} not found in mapping"
                )

            # Check if tag exists in cache
            if name not in self._cache:
                logger.error(f"Tag {name} not found in cache")
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Tag {name} not found in cache"
                )

            # Get value from cache
            value = self._cache[name].value
            logger.debug(f"Read tag {name} = {value}")
            return value

        except Exception as e:
            error_msg = f"Failed to read tag {name}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def write_tag(self, name: str, value: Any) -> None:
        """Write tag value to PLC and cache.
        
        Args:
            name: Internal tag name
            value: Tag value
            
        Raises:
            HTTPException: If write fails or service not running
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Map internal name to PLC tag
            plc_name = self._tag_mapping.get_plc_tag(name)
            if not plc_name:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"No PLC tag mapping found for {name}"
                )

            try:
                # Write to PLC
                await self._plc.write_tag(plc_name, value)
            except Exception as e:
                self._connection_errors += 1
                if self._connection_errors >= self._max_connection_errors:
                    await self.stop()
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message=f"Failed to write to PLC: {str(e)}"
                )

            # Update cache with internal name
            self._cache[name] = TagValue(
                name=name,
                value=value,
                timestamp=datetime.now().timestamp(),
                is_internal=False
            )

            # Reset error count on successful write
            self._connection_errors = 0

        except Exception as e:
            error_msg = f"Failed to write tag {name}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def write_internal(self, name: str, value: Any) -> None:
        """Write internal tracked value to cache (e.g. SSH P-tags).
        
        Args:
            name: Value name
            value: Value to store
            
        Raises:
            HTTPException: If service not running
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            self._cache[name] = TagValue(
                name=name,
                value=value,
                timestamp=datetime.now().timestamp(),
                is_internal=True
            )

        except Exception as e:
            error_msg = f"Failed to write internal value {name}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Health status dictionary
        """
        try:
            uptime = (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
            
            return {
                "status": "ok" if self.is_running else "error",
                "service": self._service_name,
                "version": self._version,
                "running": self.is_running,
                "uptime": uptime,
                "tag_count": len(self._cache),
                "plc_connected": self._plc.is_connected,
                "connection_errors": self._connection_errors
            }
        except Exception as e:
            error_msg = "Failed to get health status"
            logger.error(f"{error_msg}: {str(e)}")
            return {
                "status": "error",
                "service": self._service_name,
                "version": self._version,
                "running": False,
                "error": str(e)
            }
