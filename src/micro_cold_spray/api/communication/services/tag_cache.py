"""Tag cache service implementation."""

from typing import Dict, Any, Set
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config import ConfigService
from micro_cold_spray.api.communication.services.tag_mapping import TagMappingService
from micro_cold_spray.api.communication.models.tags import TagValue, TagMetadata, TagCacheResponse


class TagCacheService(ConfigurableService):
    """Service for caching and validating tag values."""

    def __init__(self, config_service: ConfigService):
        """Initialize tag cache service.
        
        Args:
            config_service: Configuration service instance
        """
        super().__init__(service_name="tag_cache", config_service=config_service)
        self._tag_mapping: TagMappingService = None
        self._cache: Dict[str, TagValue] = {}

    async def _start(self) -> None:
        """Initialize service."""
        try:
            logger.debug("Initializing tag mapping service")
            # Initialize tag mapping
            self._tag_mapping = TagMappingService(self._config_service)
            await self._tag_mapping.start()
            
            # Load tag definitions
            logger.debug("Loading tag configuration")
            tag_config = await self._config_service.get_config("tags")
            if not tag_config:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Tag configuration not found"
                )
                
            logger.debug("Building tag cache")
            await self._build_cache(tag_config)
            logger.info("Tag cache initialized")
        except Exception as e:
            logger.error(f"Failed to start tag cache service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start tag cache service: {e}",
                context={"error": str(e)},
                cause=e
            )

    async def _stop(self) -> None:
        """Cleanup service."""
        if self._tag_mapping:
            await self._tag_mapping.stop()
            
        self._cache.clear()
        logger.info("Tag cache stopped")

    async def _build_cache(self, config: Dict[str, Any]) -> None:
        """Build tag cache from config."""
        try:
            self._cache.clear()
            
            for group_name, group in config.get("tag_groups", {}).items():
                for tag_path, tag_def in group.items():
                    mapped_name = f"{group_name}.{tag_path}"
                    
                    # Create tag metadata
                    metadata = TagMetadata(
                        name=mapped_name,
                        description=tag_def.get("description", ""),
                        units=tag_def.get("units", ""),
                        min_value=tag_def.get("min"),
                        max_value=tag_def.get("max"),
                        is_mapped=tag_def.get("mapped", False)
                    )
                    
                    # Initialize tag value
                    self._cache[mapped_name] = TagValue(
                        metadata=metadata,
                        value=None,
                        timestamp=datetime.now()
                    )
                    
            logger.info(f"Built cache for {len(self._cache)} tags")
            
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to build tag cache",
                context={"error": str(e)},
                cause=e
            )

    async def get_tag(self, tag_path: str) -> TagValue:
        """Get tag value and metadata.
        
        Args:
            tag_path: Tag path to get
            
        Returns:
            Tag value and metadata
            
        Raises:
            HTTPException: If tag not found
        """
        try:
            return self._cache[tag_path]
        except KeyError:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Tag not found: {tag_path}",
                context={"tag": tag_path}
            )

    async def update_tag(self, tag_path: str, value: Any) -> None:
        """Update tag value.
        
        Args:
            tag_path: Tag to update
            value: New value
            
        Raises:
            HTTPException: If tag not found or validation fails
        """
        try:
            tag = self._cache[tag_path]
            
            # Validate value range if defined
            if tag.metadata.min_value is not None and value < tag.metadata.min_value:
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message=f"Value {value} below minimum {tag.metadata.min_value}",
                    context={
                        "tag": tag_path,
                        "value": value,
                        "min": tag.metadata.min_value
                    }
                )
                
            if tag.metadata.max_value is not None and value > tag.metadata.max_value:
                raise create_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    message=f"Value {value} above maximum {tag.metadata.max_value}",
                    context={
                        "tag": tag_path,
                        "value": value,
                        "max": tag.metadata.max_value
                    }
                )
                
            # Update value and timestamp
            tag.value = value
            tag.timestamp = datetime.now()
            
        except KeyError:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Tag not found: {tag_path}",
                context={"tag": tag_path}
            )
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to update tag {tag_path}",
                context={"tag": tag_path, "value": value, "error": str(e)},
                cause=e
            )

    async def get_all_tags(self) -> TagCacheResponse:
        """Get all tag values and metadata.
        
        Returns:
            All tag values and metadata
        """
        return TagCacheResponse(
            tags=self._cache,
            timestamp=datetime.now()
        )

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        try:
            # Service is running if we have a valid cache and tag mapping service
            return (
                self._cache is not None and
                self._tag_mapping is not None and
                self._tag_mapping.is_running
            )
        except Exception as e:
            logger.error(f"Error checking tag cache service status: {e}")
            return False

    async def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            status = {
                "cache_initialized": self._cache is not None,
                "tag_mapping": self._tag_mapping is not None and self._tag_mapping.is_running,
                "tag_count": len(self._cache) if self._cache is not None else 0
            }
            
            details = {}
            if not status["cache_initialized"]:
                details["cache"] = "Tag cache not initialized"
            if not status["tag_mapping"]:
                details["tag_mapping"] = "Tag mapping service not running"
            if status["tag_count"] == 0:
                details["tags"] = "No tags in cache"
                
            return {
                "status": "ok" if all(status.values()) and status["tag_count"] > 0 else "error",
                "components": status,
                "details": details if details else None
            }
        except Exception as e:
            error_msg = f"Failed to check tag cache health: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
