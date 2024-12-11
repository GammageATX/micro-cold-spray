"""Tag cache service implementation."""

from typing import Dict, Any, Set
from datetime import datetime
from loguru import logger

from .. import HardwareError
from .tag_mapping import TagMappingService
from ..models.tags import TagValue, TagMetadata, TagCacheResponse


class ValidationError(HardwareError):
    """Raised when tag validation fails."""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        super().__init__(message, "validation", context)


class TagCacheService:
    """Service for caching and validating tag values."""

    def __init__(self, config_service):
        """Initialize tag cache service."""
        self._config_service = config_service
        self._tag_mapping: TagMappingService = None
        self._cache: Dict[str, TagValue] = {}
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def start(self) -> None:
        """Initialize service."""
        # Initialize tag mapping
        self._tag_mapping = TagMappingService(self._config_service)
        await self._tag_mapping.start()
        
        # Load tag definitions
        tag_config = await self._config_service.get_config("tags")
        await self._build_cache(tag_config)
        
        self._is_running = True
        logger.info("Tag cache initialized")

    async def stop(self) -> None:
        """Cleanup service."""
        self._is_running = False
        
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
                    metadata = TagMetadata(
                        type=tag_def["type"],
                        access=tag_def["access"],
                        description=tag_def.get("description", ""),
                        unit=tag_def.get("unit"),
                        range=tag_def.get("range"),
                        states=tag_def.get("states"),
                        options=tag_def.get("options"),
                        internal=not tag_def.get("mapped", False),
                        group=group_name
                    )
                    
                    full_path = f"{group_name}.{tag_path}"
                    self._cache[full_path] = TagValue(
                        value=None,
                        metadata=metadata,
                        timestamp=datetime.now()
                    )
                    
            logger.info(f"Built cache with {len(self._cache)} tags")
        except Exception as e:
            raise HardwareError(
                "Failed to build tag cache",
                "cache",
                {"error": str(e)}
            )

    def update_tag(self, tag_path: str, value: Any) -> None:
        """Update tag value in cache."""
        if not self.is_running:
            raise HardwareError(
                "Tag cache not running",
                "cache",
                {"tag_path": tag_path}
            )
            
        if tag_path not in self._cache:
            raise HardwareError(
                f"Tag not in cache: {tag_path}",
                "cache",
                {"tag_path": tag_path}
            )
            
        try:
            # Validate value before caching
            self.validate_value(tag_path, value)
            
            # Update cache
            self._cache[tag_path] = TagValue(
                value=value,
                metadata=self._cache[tag_path].metadata,
                timestamp=datetime.now()
            )
        except ValidationError as e:
            raise ValidationError(
                f"Invalid value for {tag_path}: {str(e)}",
                {"tag_path": tag_path, "value": value}
            )

    def validate_value(self, tag_path: str, value: Any) -> None:
        """Validate value against tag metadata."""
        if not self.is_running:
            raise HardwareError(
                "Tag cache not running",
                "cache",
                {"tag_path": tag_path}
            )
            
        if tag_path not in self._cache:
            raise HardwareError(
                f"Tag not in cache: {tag_path}",
                "cache",
                {"tag_path": tag_path}
            )
            
        metadata = self._cache[tag_path].metadata
        
        # Type validation
        if metadata.type == "float":
            if not isinstance(value, (int, float)):
                raise ValidationError(
                    "Value must be numeric",
                    {"tag_path": tag_path, "value": value, "type": metadata.type}
                )
        elif metadata.type == "bool":
            if not isinstance(value, bool):
                raise ValidationError(
                    "Value must be boolean",
                    {"tag_path": tag_path, "value": value, "type": metadata.type}
                )
        elif metadata.type == "string":
            if not isinstance(value, str):
                raise ValidationError(
                    "Value must be string",
                    {"tag_path": tag_path, "value": value, "type": metadata.type}
                )
                
        # Range validation
        if metadata.range and isinstance(value, (int, float)):
            min_val, max_val = metadata.range
            if value < min_val or value > max_val:
                raise ValidationError(
                    f"Value out of range [{min_val}, {max_val}]",
                    {
                        "tag_path": tag_path,
                        "value": value,
                        "range": metadata.range
                    }
                )
                
        # Options validation
        if metadata.options and isinstance(value, str):
            if value not in metadata.options:
                raise ValidationError(
                    f"Invalid option. Must be one of: {metadata.options}",
                    {
                        "tag_path": tag_path,
                        "value": value,
                        "options": metadata.options
                    }
                )

    def get_tag(self, tag_path: str) -> Any:
        """Get tag value from cache."""
        if not self.is_running:
            raise HardwareError(
                "Tag cache not running",
                "cache",
                {"tag_path": tag_path}
            )
            
        if tag_path not in self._cache:
            raise HardwareError(
                f"Tag not in cache: {tag_path}",
                "cache",
                {"tag_path": tag_path}
            )
            
        return self._cache[tag_path].value

    def get_tag_with_metadata(self, tag_path: str) -> TagValue:
        """Get tag value with metadata."""
        if not self.is_running:
            raise HardwareError(
                "Tag cache not running",
                "cache",
                {"tag_path": tag_path}
            )
            
        if tag_path not in self._cache:
            raise HardwareError(
                f"Tag not in cache: {tag_path}",
                "cache",
                {"tag_path": tag_path}
            )
            
        return self._cache[tag_path]

    def filter_tags(
        self,
        groups: Set[str] = None,
        types: Set[str] = None,
        access: Set[str] = None
    ) -> TagCacheResponse:
        """Get filtered tag values."""
        if not self.is_running:
            raise HardwareError(
                "Tag cache not running",
                "cache"
            )
            
        try:
            filtered_tags = {}
            for tag_path, tag_value in self._cache.items():
                # Apply filters
                if groups and tag_value.metadata.group not in groups:
                    continue
                    
                if types and tag_value.metadata.type not in types:
                    continue
                    
                if access and tag_value.metadata.access not in access:
                    continue
                    
                filtered_tags[tag_path] = tag_value
                
            # Get unique groups in response
            result_groups = {v.metadata.group for v in filtered_tags.values()}
                
            return TagCacheResponse(
                tags=filtered_tags,
                timestamp=datetime.now(),
                groups=result_groups
            )
        except Exception as e:
            raise HardwareError(
                "Failed to filter tags",
                "cache",
                {"error": str(e)}
            )

    async def check_status(self) -> bool:
        """Check if cache is healthy."""
        try:
            return self.is_running and bool(self._cache)
        except Exception as e:
            logger.error(f"Cache status check failed: {str(e)}")
            return False
