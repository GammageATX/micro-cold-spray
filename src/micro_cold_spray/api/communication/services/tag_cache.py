"""Tag cache service implementation."""

from typing import Dict, Any, List
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.models.tags import TagValue, TagMetadata, TagCacheResponse


class TagCacheService:
    """Service for caching and validating tag values."""

    def __init__(self):
        """Initialize tag cache service."""
        self._service_name = "tag_cache"
        self._cache: Dict[str, TagValue] = {}
        self._is_running = False
        logger.info("TagCacheService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def start(self) -> None:
        """Start tag cache service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Initialize cache
            self._cache.clear()
            self._is_running = True
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
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running"
                )

            self._cache.clear()
            self._is_running = False
            logger.info("Tag cache service stopped")

        except Exception as e:
            error_msg = f"Failed to stop tag cache service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def read_tag(self, tag_id: str) -> Any:
        """Read tag value from cache.
        
        Args:
            tag_id: Tag identifier
            
        Returns:
            Tag value
            
        Raises:
            HTTPException: If tag not found or read fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if tag_id not in self._cache:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Tag {tag_id} not found"
                )

            return self._cache[tag_id].value

        except Exception as e:
            error_msg = f"Failed to read tag {tag_id}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def write_tag(self, tag_id: str, value: Any, data_type: str = None) -> None:
        """Write tag value to cache.
        
        Args:
            tag_id: Tag identifier
            value: Value to write
            data_type: Optional data type override
            
        Raises:
            HTTPException: If tag not found or write fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            # Create or update tag value
            self._cache[tag_id] = TagValue(
                metadata=TagMetadata(
                    name=tag_id,
                    description=f"Tag {tag_id}",
                    units="",
                    min_value=None,
                    max_value=None,
                    is_mapped=True
                ),
                value=value,
                timestamp=datetime.now()
            )
            logger.debug(f"Updated tag {tag_id} = {value}")

        except Exception as e:
            error_msg = f"Failed to write tag {tag_id}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def list_tags(self) -> List[Dict[str, Any]]:
        """List available tags.
        
        Returns:
            List of tag metadata
            
        Raises:
            HTTPException: If listing fails
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            return [
                {
                    "tag_id": tag_id,
                    "name": tag.metadata.name,
                    "description": tag.metadata.description,
                    "units": tag.metadata.units,
                    "is_mapped": tag.metadata.is_mapped,
                    "last_update": tag.timestamp
                }
                for tag_id, tag in self._cache.items()
            ]

        except Exception as e:
            error_msg = "Failed to list tags"
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
        return {
            "status": "ok" if self.is_running else "error",
            "service": self._service_name,
            "running": self.is_running,
            "cache_size": len(self._cache)
        }
