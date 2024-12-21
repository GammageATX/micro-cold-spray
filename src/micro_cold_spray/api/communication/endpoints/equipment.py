"""Equipment endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.services.equipment import EquipmentService
from micro_cold_spray.api.communication.dependencies import get_equipment_service


router = APIRouter(
    prefix="/equipment",
    tags=["equipment"]
)


@router.get("/health")
async def check_health(
    service: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, Any]:
    """Check equipment service health.
    
    Returns:
        Health status dictionary
    """
    try:
        is_healthy = await service.check_health()
        return {
            "status": "ok" if is_healthy else "error",
            "service": {
                "name": service.name,
                "running": service.is_running and is_healthy
            }
        }
    except Exception as e:
        logger.error(f"Failed to check equipment service health: {str(e)}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Failed to check equipment service health"
        )


@router.post("/gas/{action}")
async def control_gas(
    action: str,
    service: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, str]:
    """Control gas system.
    
    Args:
        action: Action to perform (on/off)
        
    Returns:
        Success message
    """
    if action not in ["on", "off"]:
        raise create_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid gas control action"
        )
        
    try:
        if action == "on":
            await service.start_gas()
        else:
            await service.stop_gas()
            
        return {"message": f"Gas system turned {action}"}
    except Exception as e:
        logger.error(f"Failed to control gas system ({action}): {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to control gas system ({action})"
        )


@router.post("/vacuum/{action}")
async def control_vacuum(
    action: str,
    service: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, str]:
    """Control vacuum system.
    
    Args:
        action: Action to perform (on/off)
        
    Returns:
        Success message
    """
    if action not in ["on", "off"]:
        raise create_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid vacuum control action"
        )
        
    try:
        if action == "on":
            await service.start_vacuum()
        else:
            await service.stop_vacuum()
            
        return {"message": f"Vacuum system turned {action}"}
    except Exception as e:
        logger.error(f"Failed to control vacuum system ({action}): {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to control vacuum system ({action})"
        )


@router.post("/feeder/{action}")
async def control_feeder(
    action: str,
    service: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, str]:
    """Control powder feeder.
    
    Args:
        action: Action to perform (on/off)
        
    Returns:
        Success message
    """
    if action not in ["on", "off"]:
        raise create_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid feeder control action"
        )
        
    try:
        if action == "on":
            await service.start_feeder()
        else:
            await service.stop_feeder()
            
        return {"message": f"Powder feeder turned {action}"}
    except Exception as e:
        logger.error(f"Failed to control powder feeder ({action}): {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to control powder feeder ({action})"
        )


@router.post("/nozzle/{action}")
async def control_nozzle(
    action: str,
    service: EquipmentService = Depends(get_equipment_service)
) -> Dict[str, str]:
    """Control spray nozzle.
    
    Args:
        action: Action to perform (on/off)
        
    Returns:
        Success message
    """
    if action not in ["on", "off"]:
        raise create_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid nozzle control action"
        )
        
    try:
        if action == "on":
            await service.start_nozzle()
        else:
            await service.stop_nozzle()
            
        return {"message": f"Spray nozzle turned {action}"}
    except Exception as e:
        logger.error(f"Failed to control spray nozzle ({action}): {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to control spray nozzle ({action})"
        )
