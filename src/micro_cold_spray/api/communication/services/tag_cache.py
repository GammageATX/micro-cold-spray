"""Tag cache service implementation."""

from typing import Dict, Any, Set
from datetime import datetime
from loguru import logger

from ...base import ConfigurableService
from ...base.exceptions import ServiceError, ValidationError
from ...config import ConfigService
from .tag_mapping import TagMappingService
from ..models.tags import TagValue, TagMetadata, TagCacheResponse


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
        # Initialize tag mapping
        self._tag_mapping = TagMappingService(self._config_service)
        await self._tag_mapping.start()
        
        # Load tag definitions
        tag_config = await self._config_service.get_config("tags")
        await self._build_cache(tag_config)
        logger.info("Tag cache initialized")

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
            
            def process_tag_group(group_name: str, group_data: Dict[str, Any], parent_path: str = "") -> None:
                """Process a group of tags recursively."""
                for tag_name, tag_data in group_data.items():
                    # Skip non-dict entries
                    if not isinstance(tag_data, dict):
                        continue
                        
                    # Build the full path
                    current_path = f"{parent_path}.{tag_name}" if parent_path else f"{group_name}.{tag_name}"
                    
                    # If this is a tag definition (has type field)
                    if "type" in tag_data:
                        metadata = TagMetadata(
                            type=tag_data["type"],
                            access=tag_data["access"],
                            description=tag_data.get("description", ""),
                            unit=tag_data.get("unit"),
                            range=tag_data.get("range"),
                            states=tag_data.get("states"),
                            options=tag_data.get("options"),
                            internal=not tag_data.get("mapped", False),
                            group=group_name
                        )
                        
                        self._cache[current_path] = TagValue(
                            value=None,
                            metadata=metadata,
                            timestamp=datetime.now()
                        )
                    # If this is a nested group, process recursively
                    else:
                        process_tag_group(group_name, tag_data, current_path)
            
            # Process all tag groups
            for group_name, group_data in config.get("tag_groups", {}).items():
                process_tag_group(group_name, group_data)
                    
            logger.info(f"Built cache with {len(self._cache)} tags")
        except Exception as e:
            raise ServiceError(
                "Failed to build tag cache",
                {"error": str(e)}
            )

    def update_tag(self, tag_path: str, value: Any) -> None:
        """Update tag value in cache."""
        if tag_path not in self._cache:
            raise ValidationError(
                f"Tag not in cache: {tag_path}",
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
        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(
                f"Failed to update tag {tag_path}",
                {"tag_path": tag_path, "value": value, "error": str(e)}
            )

    def validate_value(self, tag_path: str, value: Any) -> None:
        """Validate value against tag metadata."""
        if tag_path not in self._cache:
            raise ValidationError(
                f"Tag not in cache: {tag_path}",
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
        if tag_path not in self._cache:
            raise ValidationError(
                f"Tag not in cache: {tag_path}",
                {"tag_path": tag_path}
            )
            
        return self._cache[tag_path].value

    def get_tag_with_metadata(self, tag_path: str) -> TagValue:
        """Get tag value with metadata."""
        if tag_path not in self._cache:
            raise ValidationError(
                f"Tag not in cache: {tag_path}",
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
            raise ServiceError(
                "Failed to filter tags",
                {"error": str(e)}
            )
