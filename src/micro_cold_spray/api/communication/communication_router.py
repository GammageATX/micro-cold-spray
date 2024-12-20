"""Communication router for hardware control endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from .communication_service import CommunicationService
from .dependencies import get_communication_service


router = APIRouter(
    prefix="/communication",
    tags=["communication"]
)


@router.get("/health")
async def check_health(
    service: CommunicationService = Depends(get_communication_service)
) -> Dict[str, Any]:
    """Check communication service health.
    
    Returns:
        Health status dictionary
        
    Raises:
        HTTPException: If health check fails
    """
    try:
        is_healthy = await service.check_connection()
        return {
            "status": "ok" if is_healthy else "error",
            "service_info": {
                "name": service._service_name,
                "running": service.is_running and is_healthy
            }
        }
    except Exception as e:
        error_msg = f"Failed to check communication service health: {str(e)}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=error_msg,
            context={"service": service._service_name},
            cause=e
        )


@router.get("/tag/{tag}")
async def read_tag(
    tag: str,
    service: CommunicationService = Depends(get_communication_service)
) -> Dict[str, Any]:
    """Read tag value from hardware.
    
    Args:
        tag: Tag to read
        
    Returns:
        Tag value
        
    Raises:
        HTTPException: If read fails
    """
    try:
        value = await service.read_tag(tag)
        return {"tag": tag, "value": value}
    except Exception as e:
        error_msg = f"Failed to read tag {tag}: {str(e)}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg,
            context={"tag": tag},
            cause=e
        )


@router.post("/tag/{tag}")
async def write_tag(
    tag: str,
    value: Any,
    service: CommunicationService = Depends(get_communication_service)
) -> Dict[str, str]:
    """Write tag value to hardware.
    
    Args:
        tag: Tag to write
        value: Value to write
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If write fails
    """
    try:
        await service.write_tag(tag, value)
        return {"message": f"Successfully wrote {value} to {tag}"}
    except Exception as e:
        error_msg = f"Failed to write tag {tag}: {str(e)}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_msg,
            context={"tag": tag, "value": value},
            cause=e
        )
