"""Tag mapping service implementation."""

import os
import yaml
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth, ComponentHealth


def load_config() -> Dict[str, Any]:
    """Load tag mapping configuration.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    config_path = os.path.join("config", "tags.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


class TagMappingService:
    """Service for mapping between internal tag names and PLC tags."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize tag mapping service.
        
        Args:
            config: Service configuration
        """
        self._service_name = "tag_mapping"
        self._version = config["communication"]["services"]["tag_mapping"]["version"]
        self._is_running = False
        self._start_time = None
        self._config = config
        self._tag_map: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"{self._service_name} service initialized")

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def version(self) -> str:
        """Get service version."""
        return self._version

    @property
    def is_running(self) -> bool:
        """Get service running state."""
        return self._is_running

    @property
    def uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0

    def _load_config(self) -> None:
        """Load tag mapping configuration."""
        try:
            # Load tag configuration from YAML file
            config_path = os.path.join("config", "tags.yaml")
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Tag configuration file not found: {config_path}")
                
            with open(config_path, "r") as f:
                tag_config = yaml.safe_load(f)
            
            # Process tag mappings from hierarchical structure
            self._tag_map.clear()
            for group_name, group_tags in tag_config.get("tag_groups", {}).items():
                self._process_tag_group(group_name, group_tags)
                
            logger.info(f"Loaded {len(self._tag_map)} tag mappings")
            
        except Exception as e:
            error_msg = f"Failed to load tag configuration: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )
            
    def _process_tag_group(self, group_prefix: str, group_data: Dict[str, Any]) -> None:
        """Process a group of tags recursively."""
        logger.debug(f"Processing tag group {group_prefix} with data: {group_data}")
        
        for tag_name, tag_data in group_data.items():
            # Skip if data is None
            if tag_data is None:
                logger.warning(f"Skipping None tag data for {tag_name} in {group_prefix}")
                continue
            
            # If tag_data is a dict but doesn't have a type field, it's a subgroup
            if isinstance(tag_data, dict):
                if "type" not in tag_data:
                    logger.debug(f"Found subgroup {tag_name} in {group_prefix}")
                    self._process_tag_group(f"{group_prefix}.{tag_name}", tag_data)
                else:
                    # It's a tag definition
                    full_tag_name = f"{group_prefix}.{tag_name}"
                    logger.debug(f"Processing tag {full_tag_name} with data: {tag_data}")
                    
                    self._tag_map[full_tag_name] = {
                        "type": tag_data.get("type", "unknown"),
                        "access": tag_data.get("access", "read"),
                        "mapped": tag_data.get("mapped", True),  # Default to True if plc_tag exists
                        "plc_tag": tag_data.get("plc_tag"),
                        "description": tag_data.get("description", ""),
                        "scaling": tag_data.get("scaling"),
                        "range": tag_data.get("range"),
                        "unit": tag_data.get("unit")
                    }
                    logger.debug(f"Added tag mapping: {full_tag_name} -> {self._tag_map[full_tag_name]}")
            else:
                logger.warning(f"Unexpected tag data type for {tag_name} in {group_prefix}: {type(tag_data)}")

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )

            # Load tag configuration
            self._load_config()
            logger.info(f"{self.service_name} service initialized")

        except Exception as e:
            error_msg = f"Failed to initialize {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service already running"
                )

            if not self._tag_map:
                raise create_error(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=f"{self.service_name} service not initialized"
                )

            self._is_running = True
            self._start_time = datetime.now()
            logger.info(f"{self.service_name} service started")

        except Exception as e:
            self._is_running = False
            self._start_time = None
            error_msg = f"Failed to start {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop service."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message=f"{self.service_name} service not running"
                )
            
            # 1. Clear tag mappings
            self._tag_map.clear()
            
            # 2. Reset service state
            self._is_running = False
            self._start_time = None
            
            logger.info(f"{self.service_name} service stopped")
            
        except Exception as e:
            error_msg = f"Failed to stop {self.service_name} service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def health(self) -> ServiceHealth:
        """Get service health status."""
        try:
            # Check tag mapping status
            mapping_ok = len(self._tag_map) > 0
            
            # Build component statuses
            components = {
                "mapping": ComponentHealth(
                    status="ok" if mapping_ok else "error",
                    error=None if mapping_ok else "No tag mappings loaded"
                )
            }
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service=self.service_name,
                version=self.version,
                is_running=self.is_running,
                uptime=self.uptime,
                error=None if overall_status == "ok" else "One or more components in error state",
                components=components
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service=self.service_name,
                version=self.version,
                is_running=False,
                uptime=self.uptime,
                error=error_msg,
                components={"mapping": ComponentHealth(status="error", error=error_msg)}
            )

    def get_plc_tag(self, internal_tag: str) -> Optional[str]:
        """Get PLC tag name for internal tag."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )

        logger.debug(f"Looking up PLC tag for {internal_tag}")
        if internal_tag not in self._tag_map:
            logger.error(f"Tag not found in mapping: {internal_tag}")
            return None
            
        tag_info = self._tag_map[internal_tag]
        logger.debug(f"Found tag info: {tag_info}")
        if not tag_info.get("mapped", False):
            logger.debug(f"Tag is not mapped: {internal_tag}")
            return None
            
        plc_tag = tag_info.get("plc_tag")
        if not plc_tag:
            logger.error(f"No PLC tag defined for: {internal_tag}")
            return None
            
        return plc_tag

    def get_internal_tag(self, plc_tag: str) -> Optional[str]:
        """Get internal tag name for PLC tag."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )

        # Search for PLC tag in mappings
        for internal_name, tag_info in self._tag_map.items():
            if tag_info.get("mapped", False) and tag_info.get("plc_tag") == plc_tag:
                return internal_name
                
        logger.error(f"No mapping found for PLC tag: {plc_tag}")
        return None

    def get_tag_type(self, internal_tag: str) -> Optional[str]:
        """Get tag type."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )

        if internal_tag not in self._tag_map:
            return None
            
        return self._tag_map[internal_tag].get("type")

    def get_tag_access(self, internal_tag: str) -> Optional[str]:
        """Get tag access mode."""
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"{self.service_name} service not running"
            )

        if internal_tag not in self._tag_map:
            return None
            
        return self._tag_map[internal_tag].get("access")

    def get_tag_info(self, internal_name: str) -> Dict[str, Any]:
        """Get all tag information."""
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message=f"{self.service_name} service not running"
                )

            if internal_name not in self._tag_map:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Tag not found: {internal_name}"
                )

            return self._tag_map[internal_name]

        except Exception as e:
            error_msg = f"Failed to get tag info for {internal_name}: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )
