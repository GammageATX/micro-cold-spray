"""Dependencies for communication API."""

from typing import Optional
from fastapi import status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.communication_service import CommunicationService


# Global service instance
_service: Optional[CommunicationService] = None


def get_communication_service() -> CommunicationService:
    """Get communication service instance.
    
    Returns:
        Communication service instance
        
    Raises:
        HTTPException: If service is not initialized
    """
    if not _service:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Communication service not initialized"
        )
    return _service


def get_equipment_service():
    """Get equipment service instance."""
    service = get_communication_service()
    return service.equipment


def get_motion_service():
    """Get motion service instance."""
    service = get_communication_service()
    return service.motion


def get_tag_service():
    """Get tag service instance."""
    service = get_communication_service()
    return service.tag_cache


async def initialize_service() -> None:
    """Initialize communication service.
    
    Raises:
        HTTPException: If service fails to initialize
    """
    global _service
    try:
        if not _service:
            _service = CommunicationService()
            await _service.start()
            logger.info("Communication service initialized")
    except Exception as e:
        error_msg = f"Failed to initialize communication service: {str(e)}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg
        )


async def cleanup_service() -> None:
    """Clean up communication service.
    
    Raises:
        HTTPException: If service fails to clean up
    """
    global _service
    try:
        if _service:
            await _service.stop()
            _service = None
            logger.info("Communication service cleaned up")
    except Exception as e:
        error_msg = f"Failed to clean up communication service: {str(e)}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg
        )
