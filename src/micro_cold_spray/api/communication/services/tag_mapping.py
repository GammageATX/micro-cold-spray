"""Tag mapping service implementation."""

from typing import Dict, Any
from loguru import logger

from ...base import ConfigurableService
from ...base.exceptions import ServiceError, ValidationError
from ...config.models import ConfigUpdate


class TagMappingService(ConfigurableService):
    """Service for mapping between hardware and logical tag names."""

    def __init__(self, config_service):
        """Initialize tag mapping service."""
        super().__init__(service_name="tag_mapping")
        self._config_service = config_service
        self._hw_to_mapped: Dict[str, str] = {}
        self._mapped_to_hw: Dict[str, str] = {}
        self._plc_tags: set = set()
        self._feeder_tags: set = set()

    async def _start(self) -> None:
        """Initialize service."""
        # Load tag definitions
        tag_config = await self._config_service.get_config("tags")
        await self._build_mappings(tag_config)
        logger.info("Tag mapping initialized")

    async def _stop(self) -> None:
        """Cleanup service."""
        self._hw_to_mapped.clear()
        self._mapped_to_hw.clear()
        self._plc_tags.clear()
        self._feeder_tags.clear()
        logger.info("Tag mapping stopped")

    async def _build_mappings(self, config: Dict[str, Any]) -> None:
        """Build tag mappings from config."""
        try:
            self._hw_to_mapped.clear()
            self._mapped_to_hw.clear()
            self._plc_tags.clear()
            self._feeder_tags.clear()
            
            for group_name, group in config.get("tag_groups", {}).items():
                for tag_path, tag_def in group.items():
                    if not tag_def.get("mapped", False):
                        continue
                        
                    mapped_name = f"{group_name}.{tag_path}"
                    
                    # Handle PLC tags
                    if "plc_tag" in tag_def:
                        hw_tag = tag_def["plc_tag"]
                        self._hw_to_mapped[hw_tag] = mapped_name
                        self._mapped_to_hw[mapped_name] = hw_tag
                        self._plc_tags.add(mapped_name)
                    
                    # Handle SSH/feeder tags
                    elif "ssh" in tag_def:
                        # For SSH tags, we use the variable names as hardware tags
                        freq_var = tag_def["ssh"]["freq_var"]
                        start_var = tag_def["ssh"]["start_var"]
                        time_var = tag_def["ssh"]["time_var"]
                        
                        # Map all SSH variables for this tag
                        for var in [freq_var, start_var, time_var]:
                            self._hw_to_mapped[var] = mapped_name
                            self._mapped_to_hw[mapped_name] = var
                        self._feeder_tags.add(mapped_name)
                        
            logger.info(f"Built mappings for {len(self._mapped_to_hw)} tags")
        except Exception as e:
            raise ServiceError(
                "Failed to build tag mappings",
                {"error": str(e)}
            )

    def to_mapped_name(self, hw_tag: str) -> str:
        """Convert hardware tag to mapped name."""
        try:
            return self._hw_to_mapped[hw_tag]
        except KeyError:
            raise ValidationError(
                f"No mapping for hardware tag: {hw_tag}",
                {"hw_tag": hw_tag}
            )

    def to_hardware_tag(self, mapped_name: str) -> str:
        """Convert mapped name to hardware tag."""
        try:
            return self._mapped_to_hw[mapped_name]
        except KeyError:
            raise ValidationError(
                f"No mapping for tag: {mapped_name}",
                {"mapped_name": mapped_name}
            )

    def is_plc_tag(self, mapped_name: str) -> bool:
        """Check if tag is mapped to PLC."""
        if mapped_name not in self._mapped_to_hw:
            raise ValidationError(
                f"Unknown tag: {mapped_name}",
                {"mapped_name": mapped_name}
            )
        return mapped_name in self._plc_tags

    def is_feeder_tag(self, mapped_name: str) -> bool:
        """Check if tag is mapped to feeder."""
        if mapped_name not in self._mapped_to_hw:
            raise ValidationError(
                f"Unknown tag: {mapped_name}",
                {"mapped_name": mapped_name}
            )
        return mapped_name in self._feeder_tags

    async def get_mappings(self) -> Dict[str, str]:
        """Get all tag mappings.
        
        Returns:
            Dictionary mapping logical tag names to hardware tags.
        """
        return self._mapped_to_hw.copy()

    async def update_mapping(self, tag_path: str, plc_tag: str) -> None:
        """Update tag mapping.
        
        Args:
            tag_path: Logical tag path
            plc_tag: Hardware PLC tag
            
        Raises:
            ValidationError: If tag path is invalid
            ServiceError: If update fails
        """
        try:
            # Get current config
            tag_config = await self._config_service.get_config("tags")
            
            # Find the tag in the config
            group_name, tag_name = tag_path.split(".", 1)
            if group_name not in tag_config.get("tag_groups", {}):
                raise ValidationError(
                    f"Invalid tag group: {group_name}",
                    {"tag_path": tag_path}
                )
                
            group = tag_config["tag_groups"][group_name]
            if tag_name not in group:
                raise ValidationError(
                    f"Invalid tag: {tag_path}",
                    {"tag_path": tag_path}
                )
                
            # Update the tag definition
            tag_def = group[tag_name]
            tag_def["mapped"] = True
            tag_def["plc_tag"] = plc_tag
            
            # Save the updated config
            update = ConfigUpdate(
                config_type="tags",
                data=tag_config,
                validate=True
            )
            await self._config_service.update_config(update)
            
            # Rebuild mappings
            await self._build_mappings(tag_config)
            
        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(
                "Failed to update tag mapping",
                {
                    "tag_path": tag_path,
                    "plc_tag": plc_tag,
                    "error": str(e)
                }
            )
