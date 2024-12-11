from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .base import BaseService
from .tag_mapping import TagMappingService
from ..models.tags import TagValue, TagMetadata


class ValidationError(HardwareError):
    """Raised when tag validation fails."""
    def __init__(self, message: str):
        super().__init__(message, "validation")


class TagCacheService(BaseService):
    """Unified tag cache that abstracts hardware implementation details."""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self._tag_mapping: TagMappingService = None
        self._cache: Dict[str, TagValue] = {}

    async def initialize(self):
        """Initialize the cache service."""
        await super().initialize()
        self._tag_mapping = TagMappingService(self._config_manager)
        await self._tag_mapping.initialize()
        logger.info("Tag cache service initialized")

    def _to_hw_value(self, tag_path: str, eng_value: Any) -> Any:
        """Convert engineering value to hardware value."""
        metadata = self._tag_mapping.get_tag_metadata(tag_path)
        
        # Handle analog scaling
        if metadata.get('scaling') == '12bit_linear' or metadata.get('scaling') == '12bit_dac':
            if not isinstance(eng_value, (int, float)):
                raise ValidationError(f"Expected number for {tag_path}, got {type(eng_value)}")
            return int(eng_value * 4095 / metadata['range'][1])
            
        # Handle speed mappings
        if 'speeds' in metadata and isinstance(eng_value, str):
            speeds = metadata['speeds']
            if eng_value not in speeds:
                raise ValidationError(f"Invalid speed {eng_value} for {tag_path}")
            return speeds[eng_value]
            
        return eng_value

    def _to_eng_value(self, tag_path: str, hw_value: Any) -> Any:
        """Convert hardware value to engineering value."""
        metadata = self._tag_mapping.get_tag_metadata(tag_path)
        
        # Handle analog scaling
        if metadata.get('scaling') == '12bit_linear' or metadata.get('scaling') == '12bit_dac':
            if not isinstance(hw_value, (int, float)):
                raise ValidationError(f"Expected number for {tag_path}, got {type(hw_value)}")
            return float(hw_value) * metadata['range'][1] / 4095
            
        # Handle speed mappings
        if 'speeds' in metadata:
            speeds = metadata['speeds']
            # Find the speed name that matches this value
            for name, value in speeds.items():
                if value == hw_value:
                    return name
            return hw_value  # If no match, return as is
            
        return hw_value

    def validate_value(self, tag_path: str, eng_value: Any):
        """Validate an engineering value."""
        metadata = self._tag_mapping.get_tag_metadata(tag_path)
        
        # Skip validation for internal tags
        if metadata.get('internal', False):
            return

        # Access validation
        if 'write' not in metadata.get('access', 'read'):
            raise ValidationError(f"Tag {tag_path} is read-only")

        # Type validation
        expected_type = metadata.get('type', 'any')
        if expected_type == 'float':
            if not isinstance(eng_value, (int, float)):
                raise ValidationError(f"Expected number for {tag_path}, got {type(eng_value)}")
        elif expected_type == 'integer':
            if not isinstance(eng_value, int):
                raise ValidationError(f"Expected integer for {tag_path}, got {type(eng_value)}")
        elif expected_type == 'bool':
            if not isinstance(eng_value, bool):
                raise ValidationError(f"Expected boolean for {tag_path}, got {type(eng_value)}")
                    
        # Range validation
        if 'range' in metadata:
            min_val, max_val = metadata['range']
            if not min_val <= float(eng_value) <= max_val:
                raise ValidationError(f"Value {eng_value} out of range [{min_val}, {max_val}]")
                    
        # Options validation
        if 'options' in metadata and eng_value not in metadata['options']:
            raise ValidationError(f"Invalid option {eng_value}, must be one of {metadata['options']}")
            
        # Speed validation
        if 'speeds' in metadata and isinstance(eng_value, str) and eng_value not in metadata['speeds']:
            raise ValidationError(f"Invalid speed {eng_value}, must be one of {list(metadata['speeds'].keys())}")

    def _create_metadata(self, tag_path: str) -> TagMetadata:
        """Create metadata model from tag config."""
        raw_metadata = self._tag_mapping.get_tag_metadata(tag_path)
        return TagMetadata(
            type=raw_metadata.get('type', 'any'),
            access=raw_metadata.get('access', 'read'),
            description=raw_metadata.get('description', ''),
            unit=raw_metadata.get('unit'),
            range=raw_metadata.get('range'),
            states=raw_metadata.get('states'),
            options=raw_metadata.get('options'),
            internal=raw_metadata.get('internal', False)
        )

    def update_tag(self, tag_path: str, hw_value: Any):
        """Update a tag value in the cache using hardware value."""
        eng_value = self._to_eng_value(tag_path, hw_value)
        metadata = self._create_metadata(tag_path)
        
        self._cache[tag_path] = TagValue(
            value=eng_value,
            metadata=metadata,
            timestamp=datetime.now()
        )
        
    def get_tag(self, tag_path: str) -> Any:
        """Get a tag's engineering value from the cache."""
        if tag_path not in self._cache:
            raise HardwareError(f"Tag not in cache: {tag_path}", "cache")
        return self._cache[tag_path].value

    def get_tag_with_metadata(self, tag_path: str) -> TagValue:
        """Get a tag value with metadata."""
        if tag_path not in self._cache:
            raise HardwareError(f"Tag not in cache: {tag_path}", "cache")
        return self._cache[tag_path]

    def get_all_tags(self) -> Dict[str, TagValue]:
        """Get all tag values with metadata."""
        return self._cache

    def get_tag_timestamp(self, tag_path: str) -> datetime:
        """Get the timestamp of when a tag was last updated."""
        if tag_path not in self._cache:
            raise HardwareError(f"Tag not in cache: {tag_path}", "cache")
        return self._cache[tag_path].timestamp

    def clear_cache(self):
        """Clear all cached values."""
        self._cache.clear()
        logger.debug("Tag cache cleared")