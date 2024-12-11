"""Tag mapping service implementation."""

from typing import Dict, Any
from loguru import logger

from .. import HardwareError


class TagMappingService:
    """Service for mapping between hardware and logical tag names."""

    def __init__(self, config_service):
        """Initialize tag mapping service."""
        self._config_service = config_service
        self._hw_to_mapped: Dict[str, str] = {}
        self._mapped_to_hw: Dict[str, str] = {}
        self._plc_tags: set = set()
        self._feeder_tags: set = set()
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def start(self) -> None:
        """Initialize service."""
        # Load tag definitions
        tag_config = await self._config_service.get_config("tags")
        await self._build_mappings(tag_config)
        
        self._is_running = True
        logger.info("Tag mapping initialized")

    async def stop(self) -> None:
        """Cleanup service."""
        self._is_running = False
        
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
                    hw_tag = tag_def["hardware_tag"]
                    
                    self._hw_to_mapped[hw_tag] = mapped_name
                    self._mapped_to_hw[mapped_name] = hw_tag
                    
                    # Track tag type
                    if tag_def.get("device") == "plc":
                        self._plc_tags.add(mapped_name)
                    elif tag_def.get("device") == "feeder":
                        self._feeder_tags.add(mapped_name)
                        
            logger.info(f"Built mappings for {len(self._mapped_to_hw)} tags")
        except Exception as e:
            raise HardwareError(
                "Failed to build tag mappings",
                "mapping",
                {"error": str(e)}
            )

    def to_mapped_name(self, hw_tag: str) -> str:
        """Convert hardware tag to mapped name."""
        if not self.is_running:
            raise HardwareError(
                "Tag mapping not running",
                "mapping",
                {"hw_tag": hw_tag}
            )
            
        try:
            return self._hw_to_mapped[hw_tag]
        except KeyError:
            raise HardwareError(
                f"No mapping for hardware tag: {hw_tag}",
                "mapping",
                {"hw_tag": hw_tag}
            )

    def to_hardware_tag(self, mapped_name: str) -> str:
        """Convert mapped name to hardware tag."""
        if not self.is_running:
            raise HardwareError(
                "Tag mapping not running",
                "mapping",
                {"mapped_name": mapped_name}
            )
            
        try:
            return self._mapped_to_hw[mapped_name]
        except KeyError:
            raise HardwareError(
                f"No mapping for tag: {mapped_name}",
                "mapping",
                {"mapped_name": mapped_name}
            )

    def is_plc_tag(self, mapped_name: str) -> bool:
        """Check if tag is mapped to PLC."""
        if not self.is_running:
            raise HardwareError(
                "Tag mapping not running",
                "mapping",
                {"mapped_name": mapped_name}
            )
            
        return mapped_name in self._plc_tags

    def is_feeder_tag(self, mapped_name: str) -> bool:
        """Check if tag is mapped to feeder."""
        if not self.is_running:
            raise HardwareError(
                "Tag mapping not running",
                "mapping",
                {"mapped_name": mapped_name}
            )
            
        return mapped_name in self._feeder_tags

    async def check_status(self) -> bool:
        """Check if mapping is healthy."""
        try:
            return self.is_running and bool(self._mapped_to_hw)
        except Exception as e:
            logger.error(f"Mapping status check failed: {str(e)}")
            return False
