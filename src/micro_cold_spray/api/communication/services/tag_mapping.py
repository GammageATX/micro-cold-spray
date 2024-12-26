"""Service for mapping between internal tag names and PLC tags."""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import yaml
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import get_uptime, ServiceHealth


class TagMappingService:
    """Service for mapping between internal tag names and PLC tags."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize tag mapping service.
        
        Args:
            config: Service configuration
        """
        self._service_name = "tag_mapping"
        self._version = "1.0.0"
        self._tag_map: Dict[str, Dict[str, Any]] = {}
        self._is_running = False
        self._start_time = None
        self._config = config
        logger.info("TagMappingService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    def _load_config(self) -> None:
        """Load tag configuration from YAML file."""
        try:
            # Load and parse YAML file
            config_path = Path(self._config["communication"]["services"]["tag_mapping"]["config_file"])
            if not config_path.exists():
                raise FileNotFoundError(f"Tag config not found: {config_path}")

            logger.debug(f"Loading tag config from {config_path}")
            with open(config_path) as f:
                tag_config = yaml.safe_load(f)
                if not isinstance(tag_config, dict):
                    raise ValueError(f"Invalid tag config format - expected dict, got {type(tag_config)}")

            # Process tag groups recursively
            def process_group(group: Dict[str, Any], prefix: str = "") -> None:
                for name, data in group.items():
                    if isinstance(data, dict):
                        full_path = f"{prefix}{name}" if prefix else name
                        if "plc_tag" in data or data.get("internal", False):
                            # This is a tag definition
                            self._tag_map[full_path] = data
                            logger.debug(f"Added tag definition: {full_path} -> {data}")
                        else:
                            # This is a nested group
                            new_prefix = f"{full_path}." if full_path else f"{name}."
                            logger.debug(f"Processing group: {new_prefix}")
                            process_group(data, new_prefix)

            # Start with top level groups
            if "tag_groups" in tag_config:
                logger.debug("Processing tag groups...")
                process_group(tag_config["tag_groups"])
            else:
                # No groups - process top level directly
                logger.debug("Processing top level tags...")
                process_group(tag_config)

            # Log loaded mappings for debugging
            for internal_name, tag_info in self._tag_map.items():
                if "plc_tag" in tag_info:
                    logger.debug(f"Loaded tag mapping: {internal_name} -> {tag_info['plc_tag']}")

            logger.info(f"Loaded {len(self._tag_map)} tag definitions")

        except Exception as e:
            error_msg = f"Failed to load tag config: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def initialize(self) -> None:
        """Initialize tag mapping service.
        
        Raises:
            HTTPException: If initialization fails
        """
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Load tag configuration
            self._load_config()
            self._is_running = True
            logger.info("Tag mapping service initialized")

        except Exception as e:
            error_msg = f"Failed to initialize tag mapping service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def start(self) -> None:
        """Start tag mapping service.
        
        Raises:
            HTTPException: If startup fails
        """
        try:
            if not self.is_running:
                await self.initialize()

            self._start_time = datetime.now()
            logger.info("Tag mapping service started")

        except Exception as e:
            error_msg = f"Failed to start tag mapping service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
            )

    async def stop(self) -> None:
        """Stop tag mapping service."""
        try:
            if not self.is_running:
                return

            self._tag_map.clear()
            self._is_running = False
            self._start_time = None
            logger.info("Tag mapping service stopped")

        except Exception as e:
            error_msg = f"Failed to stop tag mapping service: {str(e)}"
            logger.error(error_msg)
            # Don't raise during shutdown

    def get_plc_tag(self, internal_tag: str) -> Optional[str]:
        """Get PLC tag name for internal tag.
        
        Args:
            internal_tag: Internal tag name
            
        Returns:
            PLC tag name if mapped, None if internal only
        """
        if not self.is_running:
            logger.error("Tag mapping service not running")
            return None

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
        """Get internal tag name for PLC tag.
        
        Args:
            plc_tag: PLC tag name
            
        Returns:
            Internal tag name if mapped, None if not found
        """
        if not self.is_running:
            logger.error("Tag mapping service not running")
            return None

        # Search for PLC tag in mappings
        for internal_name, tag_info in self._tag_map.items():
            if tag_info.get("mapped", False) and tag_info.get("plc_tag") == plc_tag:
                return internal_name
                
        logger.error(f"No mapping found for PLC tag: {plc_tag}")
        return None

    def get_tag_type(self, internal_tag: str) -> Optional[str]:
        """Get tag type.
        
        Args:
            internal_tag: Internal tag name
            
        Returns:
            Tag type if defined, None if not found
        """
        if internal_tag not in self._tag_map:
            return None
            
        return self._tag_map[internal_tag].get("type")

    def get_tag_access(self, internal_tag: str) -> Optional[str]:
        """Get tag access mode.
        
        Args:
            internal_tag: Internal tag name
            
        Returns:
            Access mode if defined, None if not found
        """
        if internal_tag not in self._tag_map:
            return None
            
        return self._tag_map[internal_tag].get("access")

    def get_tag_info(self, internal_name: str) -> Dict[str, Any]:
        """Get all tag information.
        
        Args:
            internal_name: Internal tag name
            
        Returns:
            Tag information dictionary
            
        Raises:
            HTTPException: If tag not found
        """
        try:
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if internal_name not in self._tag_map:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Tag not found: {internal_name}"
                )

            return self._tag_map[internal_name]

        except Exception as e:
            error_msg = f"Failed to get tag info for {internal_name}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def health(self) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Health status
        """
        try:
            # Check mappings status
            mappings_ok = self.is_running and isinstance(self._tag_map, dict)
            
            # Build component statuses
            components = {
                "mappings": {
                    "status": "ok" if mappings_ok else "error",
                    "error": None if mappings_ok else "Mappings not initialized"
                }
            }
            
            # Overall status is error if any component is in error
            overall_status = "error" if any(c["status"] == "error" for c in components.values()) else "ok"
            
            return ServiceHealth(
                status=overall_status,
                service="tag_mapping",
                version="1.0.0",
                is_running=self.is_running,
                uptime=get_uptime(),
                error=None if overall_status == "ok" else "One or more components in error state",
                components=components
            )
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return ServiceHealth(
                status="error",
                service="tag_mapping",
                version="1.0.0",
                is_running=False,
                uptime=0.0,
                error=error_msg,
                components={
                    "mappings": {"status": "error", "error": error_msg}
                }
            )
