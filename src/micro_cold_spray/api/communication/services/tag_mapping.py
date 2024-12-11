from typing import Dict, Any, Optional
from loguru import logger

from .base import BaseService


class TagMappingService(BaseService):
    """Handles mapping between human-readable tag names and hardware tags."""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self._mapped_to_hw: Dict[str, str] = {}
        self._hw_to_mapped: Dict[str, str] = {}
        self._tag_metadata: Dict[str, Dict[str, Any]] = {}

    async def initialize(self):
        """Initialize mappings from config."""
        await super().initialize()
        await self._build_mappings()

    async def _build_mappings(self):
        """Build bidirectional mappings from tag config."""
        self._mapped_to_hw = {}
        self._hw_to_mapped = {}
        self._tag_metadata = {}

        # Process all tag groups
        for group_name, group in self._tag_config.items():
            for tag_path, tag_data in group.get('tags', {}).items():
                # Skip unmapped tags
                if not tag_data.get('mapped', False):
                    continue

                # Full mapped name includes group
                mapped_name = f"{group_name}.{tag_path}"

                # Get hardware tag - either PLC tag or SSH P-variable
                hw_tag = tag_data.get('plc_tag')
                if not hw_tag and tag_data.get('ssh', {}).get('freq_var'):
                    hw_tag = tag_data['ssh']['freq_var']

                if hw_tag:
                    self._mapped_to_hw[mapped_name] = hw_tag
                    self._hw_to_mapped[hw_tag] = mapped_name
                    self._tag_metadata[mapped_name] = tag_data

        logger.info(f"Built tag mappings for {len(self._mapped_to_hw)} tags")

    def to_hardware_tag(self, mapped_name: str) -> str:
        """Convert mapped name to hardware tag."""
        if mapped_name not in self._mapped_to_hw:
            raise HardwareError(f"Unknown mapped tag: {mapped_name}", "mapping")
        return self._mapped_to_hw[mapped_name]

    def to_mapped_name(self, hardware_tag: str) -> str:
        """Convert hardware tag to mapped name."""
        if hardware_tag not in self._hw_to_mapped:
            raise HardwareError(f"Unknown hardware tag: {hardware_tag}", "mapping")
        return self._hw_to_mapped[hardware_tag]

    def get_tag_metadata(self, mapped_name: str) -> Dict[str, Any]:
        """Get metadata for a mapped tag."""
        if mapped_name not in self._tag_metadata:
            raise HardwareError(f"Unknown mapped tag: {mapped_name}", "mapping")
        return self._tag_metadata[mapped_name]

    def is_plc_tag(self, mapped_name: str) -> bool:
        """Check if tag is a PLC tag."""
        metadata = self.get_tag_metadata(mapped_name)
        return 'plc_tag' in metadata

    def is_feeder_tag(self, mapped_name: str) -> bool:
        """Check if tag is a feeder tag."""
        metadata = self.get_tag_metadata(mapped_name)
        return bool(metadata.get('ssh', {}).get('freq_var'))

    async def _on_tag_config_update(self):
        """Handle tag config updates."""
        await self._build_mappings() 