"""Tag mapping service implementation."""

from typing import Dict, Any
from fastapi import status
from loguru import logger

from micro_cold_spray.utils.errors import create_error


class TagMappingService:
    """Service for mapping tag names to hardware addresses."""

    def __init__(self):
        """Initialize tag mapping service."""
        self._service_name = "tag_mapping"
        self._tag_map: Dict[str, str] = {}
        self._reverse_map: Dict[str, str] = {}
        self._is_running = False
        logger.info("TagMappingService initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._is_running

    async def start(self) -> None:
        """Start tag mapping service."""
        try:
            if self.is_running:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service already running"
                )

            # Initialize maps
            self._tag_map.clear()
            self._reverse_map.clear()
            self._is_running = True
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
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Service not running"
                )

            self._tag_map.clear()
            self._reverse_map.clear()
            self._is_running = False
            logger.info("Tag mapping service stopped")

        except Exception as e:
            error_msg = f"Failed to stop tag mapping service: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=error_msg
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
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if tag_path not in self._tag_map:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Tag not found or not mapped: {tag_path}"
                )

            return self._tag_map[tag_path]

        except Exception as e:
            error_msg = f"Failed to get address for tag {tag_path}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
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
            if not self.is_running:
                raise create_error(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    message="Service not running"
                )

            if address not in self._reverse_map:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Address not mapped: {address}"
                )

            return self._reverse_map[address]

        except Exception as e:
            error_msg = f"Failed to get tag path for address {address}"
            logger.error(f"{error_msg}: {str(e)}")
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )

    async def health(self) -> Dict[str, Any]:
        """Get service health status.
        
        Returns:
            Health status dictionary
        """
        return {
            "status": "ok" if self.is_running else "error",
            "service": self._service_name,
            "running": self.is_running,
            "tag_count": len(self._tag_map)
        }
