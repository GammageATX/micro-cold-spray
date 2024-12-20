"""Tag mapping service implementation."""

from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_configurable import ConfigurableService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config import ConfigService


class TagMappingService(ConfigurableService):
    """Service for mapping tag names to hardware addresses."""

    def __init__(self, config_service: ConfigService):
        """Initialize tag mapping service.
        
        Args:
            config_service: Configuration service instance
        """
        super().__init__(service_name="tag_mapping", config_service=config_service)
        self._tag_map: Dict[str, str] = {}
        self._reverse_map: Dict[str, str] = {}

    async def _start(self) -> None:
        """Initialize service."""
        try:
            logger.debug("Loading tag configuration")
            tag_config = await self._config_service.get_config("tags")
            if not tag_config:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Tag configuration not found"
                )
                
            logger.debug("Building tag mapping")
            await self._build_mapping(tag_config)
            logger.info("Tag mapping initialized")
        except Exception as e:
            logger.error(f"Failed to start tag mapping service: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start tag mapping service: {e}",
                context={"error": str(e)},
                cause=e
            )

    async def _stop(self) -> None:
        """Cleanup service."""
        self._tag_map.clear()
        self._reverse_map.clear()
        logger.info("Tag mapping stopped")

    async def _build_mapping(self, config: Dict[str, Any]) -> None:
        """Build tag mapping from config."""
        try:
            self._tag_map.clear()
            self._reverse_map.clear()
            
            for group_name, group in config.get("tag_groups", {}).items():
                for tag_path, tag_def in group.items():
                    mapped_name = f"{group_name}.{tag_path}"
                    
                    # Only map tags that have hardware addresses
                    if tag_def.get("mapped", False):
                        address = tag_def.get("address")
                        if not address:
                            logger.warning(f"Mapped tag {mapped_name} missing address")
                            continue
                            
                        self._tag_map[mapped_name] = address
                        self._reverse_map[address] = mapped_name
                        
            logger.info(f"Built mapping for {len(self._tag_map)} tags")
            
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to build tag mapping",
                context={"error": str(e)},
                cause=e
            )

    def get_address(self, tag_path: str) -> str:
        """Get hardware address for tag.
        
        Args:
            tag_path: Tag path to lookup
            
        Returns:
            Hardware address
            
        Raises:
            HTTPException: If tag not found or not mapped
        """
        try:
            return self._tag_map[tag_path]
        except KeyError:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Tag not found or not mapped: {tag_path}",
                context={"tag": tag_path}
            )

    def get_tag_path(self, address: str) -> str:
        """Get tag path for hardware address.
        
        Args:
            address: Hardware address to lookup
            
        Returns:
            Tag path
            
        Raises:
            HTTPException: If address not mapped
        """
        try:
            return self._reverse_map[address]
        except KeyError:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Address not mapped: {address}",
                context={"address": address}
            )

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        try:
            # Service is running if we have valid mappings
            return len(self._tag_map) > 0 and len(self._reverse_map) > 0
        except Exception as e:
            logger.error(f"Error checking tag mapping service status: {e}")
            return False

    async def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            status = {
                "tag_map": len(self._tag_map) > 0,
                "reverse_map": len(self._reverse_map) > 0,
                "tag_count": len(self._tag_map)
            }
            
            details = {}
            if not status["tag_map"]:
                details["tag_map"] = "Tag map is empty"
            if not status["reverse_map"]:
                details["reverse_map"] = "Reverse map is empty"
            if status["tag_count"] == 0:
                details["tags"] = "No tags mapped"
                
            return {
                "status": "ok" if all(status.values()) and status["tag_count"] > 0 else "error",
                "components": status,
                "details": details if details else None
            }
        except Exception as e:
            error_msg = f"Failed to check tag mapping health: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
