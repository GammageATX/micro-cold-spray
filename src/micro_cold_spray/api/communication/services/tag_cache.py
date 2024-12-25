"""Service for caching PLC tag values."""

from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from loguru import logger

from micro_cold_spray.api.communication.clients.base import CommunicationClient
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService
from micro_cold_spray.utils.errors import create_error


class TagCacheService:
    """Service for caching PLC tag values."""

    def __init__(self, client: CommunicationClient, tag_mapping: TagMappingService, poll_interval: float = 0.2):
        """Initialize tag cache service.
        
        Args:
            client: Communication client (PLC or mock)
            tag_mapping: Tag mapping service
            poll_interval: Tag polling interval in seconds
        """
        self._service_name = "tag_cache"
        self._version = "1.0.0"
        self._client = client
        self._tag_mapping = tag_mapping
        self._poll_interval = poll_interval
        self._tag_cache: Dict[str, Any] = {}  # Cache stores raw PLC tag values
        self._internal_cache: Dict[str, Any] = {}  # Cache for internal tags
        self._is_running = False
        self._start_time = None
        self._poll_task = None
        logger.info("TagCacheService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def read_tag(self, internal_tag: str) -> Optional[Any]:
        """Read tag value from cache.
        
        Args:
            internal_tag: Internal tag name
            
        Returns:
            Tag value if found, None if not in cache
            
        Raises:
            HTTPException: If read fails
        """
        try:
            # Check internal cache first
            if internal_tag in self._internal_cache:
                return self._internal_cache[internal_tag]
                
            # Map internal tag to PLC tag
            plc_tag = self._tag_mapping.get_plc_tag(internal_tag)
            if not plc_tag:
                logger.warning(f"No PLC tag mapping found for {internal_tag}")
                return None
                
            # Return value from cache if exists
            return self._tag_cache.get(plc_tag)

        except Exception as e:
            error_msg = f"Failed to read tag {internal_tag}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=500,
                message=error_msg
            )

    async def write_tag(self, internal_tag: str, value: Any) -> None:
        """Write tag value.
        
        Args:
            internal_tag: Internal tag name
            value: Value to write
            
        Raises:
            HTTPException: If write fails
        """
        try:
            # Handle internal tags
            if internal_tag in self._internal_cache:
                self._internal_cache[internal_tag] = value
                logger.debug(f"Wrote internal tag: {internal_tag} = {value}")
                return
                
            # Map internal tag to PLC tag
            plc_tag = self._tag_mapping.get_plc_tag(internal_tag)
            if not plc_tag:
                raise create_error(
                    status_code=400,
                    message=f"No PLC tag mapping found for {internal_tag}"
                )
                
            # Write to PLC and update cache
            await self._client.write_tag(plc_tag, value)
            self._tag_cache[plc_tag] = value
            logger.debug(f"Wrote PLC tag: {plc_tag} = {value}")

        except Exception as e:
            error_msg = f"Failed to write tag {internal_tag}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=500,
                message=error_msg
            )

    def get_tag_value(self, internal_tag: str) -> Optional[Any]:
        """Get cached tag value.
        
        Args:
            internal_tag: Internal tag name
            
        Returns:
            Tag value if found, None if not in cache
        """
        # Check internal cache first
        if internal_tag in self._internal_cache:
            return self._internal_cache[internal_tag]
            
        # Map internal tag to PLC tag
        plc_tag = self._tag_mapping.get_plc_tag(internal_tag)
        if not plc_tag:
            return None
            
        # Return value from cache if exists
        return self._tag_cache.get(plc_tag)

    def get_all_tag_values(self) -> Dict[str, Any]:
        """Get all cached tag values mapped to internal names.
        
        Returns:
            Dict of internal tag names to values
        """
        result = {}
        # Add mapped PLC tags
        for plc_tag, value in self._tag_cache.items():
            internal_tag = self._tag_mapping.get_internal_tag(plc_tag)
            if internal_tag:
                result[internal_tag] = value
                
        # Add internal tags
        result.update(self._internal_cache)
        return result

    def set_internal_tag(self, tag: str, value: Any) -> None:
        """Set internal tag value.
        
        Args:
            tag: Internal tag name
            value: Tag value
        """
        self._internal_cache[tag] = value
        logger.debug(f"Set internal tag: {tag} = {value}")

    async def initialize(self) -> None:
        """Initialize tag cache service.
        
        Raises:
            HTTPException: If initialization fails
        """
        try:
            if self.is_running:
                raise create_error(
                    status_code=409,
                    message="Service already running"
                )

            logger.info("Connecting to PLC...")
            await self._client.connect()
            logger.info("Connected to PLC")
            
            logger.info("Starting polling task...")
            self._poll_task = asyncio.create_task(self._poll_tags())
            self._is_running = True  # Set running state after successful initialization
            self._start_time = datetime.now()
            logger.info("Tag cache service initialized")

        except Exception as e:
            error_msg = f"Failed to initialize tag cache service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=503,
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

            logger.info("Tag cache service started")

        except Exception as e:
            error_msg = f"Failed to start tag cache service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=503,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop tag cache service."""
        try:
            if not self.is_running:
                return

            if self._poll_task:
                self._poll_task.cancel()
                try:
                    await self._poll_task
                except asyncio.CancelledError:
                    pass
                self._poll_task = None

            await self._client.disconnect()
            self._tag_cache.clear()
            self._internal_cache.clear()
            self._is_running = False
            self._start_time = None
            logger.info("Tag cache service stopped")

        except Exception as e:
            error_msg = f"Failed to stop tag cache service: {str(e)}"
            logger.error(error_msg)
            # Don't raise during shutdown

    async def _poll_tags(self) -> None:
        """Poll PLC tags and update cache."""
        last_values = {}  # Store last values to check for changes
        
        while True:
            try:
                # Get all tag values at once
                values = await self._client.get()
                if not values:
                    logger.warning("No tag values received from PLC")
                    await asyncio.sleep(self._poll_interval)
                    continue

                # Update cache with new values and log changes
                for plc_tag, new_value in values.items():
                    if plc_tag not in last_values or last_values[plc_tag] != new_value:
                        last_values[plc_tag] = new_value
                        self._tag_cache[plc_tag] = new_value

            except asyncio.CancelledError:
                logger.info("Tag polling cancelled")
                break
            except Exception as e:
                logger.error(f"Error polling tags: {str(e)}")

            await asyncio.sleep(self._poll_interval)

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
                "tag_count": len(self._tag_cache) + len(self._internal_cache)
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
