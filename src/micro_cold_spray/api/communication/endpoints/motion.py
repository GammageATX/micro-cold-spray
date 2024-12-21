"""Motion endpoints."""

from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, status, Depends
from pydantic import BaseModel, Field
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.communication.services.motion import MotionService
from micro_cold_spray.api.communication.dependencies import get_motion_service


class MotionResponse(BaseModel):
    """Motion response model."""
    status: str
    message: str
    timestamp: datetime


class MotionStatusResponse(BaseModel):
    """Motion status response model."""
    status: str
    axis_id: str
    state: Dict[str, Any]
    timestamp: datetime


class MotionListResponse(BaseModel):
    """Motion list response model."""
    status: str
    axes: List[Dict[str, Any]]
    timestamp: datetime


class MoveRequest(BaseModel):
    """Move request model."""
    axis_id: str = Field(..., description="Axis to move")
    position: float = Field(..., description="Target position")
    velocity: float = Field(None, description="Optional velocity override")


router = APIRouter(prefix="/motion", tags=["motion"])


@router.get("/status/{axis_id}")
async def get_axis_status(
    axis_id: str,
    service: MotionService = Depends(get_motion_service)
) -> MotionStatusResponse:
    """Get axis status.
    
    Args:
        axis_id: Axis identifier
        
    Returns:
        Axis status response
    """
    try:
        logger.debug(f"Getting status for axis {axis_id}")
        status_data = await service.get_status(axis_id)
        
        return MotionStatusResponse(
            status="ok",
            axis_id=axis_id,
            state=status_data,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get status for axis {axis_id}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to get status for axis {axis_id}"
        )


@router.get("/list")
async def list_axes(
    service: MotionService = Depends(get_motion_service)
) -> MotionListResponse:
    """List available axes.
    
    Returns:
        List of available axes
    """
    try:
        logger.debug("Listing available axes")
        axes_list = await service.list_axes()
        
        return MotionListResponse(
            status="ok",
            axes=axes_list,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to list axes: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to list axes"
        )


@router.post("/move")
async def move_axis(
    request: MoveRequest,
    service: MotionService = Depends(get_motion_service)
) -> MotionResponse:
    """Move axis to position.
    
    Args:
        request: Move request parameters
        
    Returns:
        Move response
    """
    try:
        logger.debug(f"Moving axis {request.axis_id} to position {request.position}")
        await service.move_axis(
            axis_id=request.axis_id,
            position=request.position,
            velocity=request.velocity
        )
        
        return MotionResponse(
            status="ok",
            message=f"Moving axis {request.axis_id} to position {request.position}",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to move axis {request.axis_id}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to move axis {request.axis_id}"
        )


@router.post("/stop/{axis_id}")
async def stop_axis(
    axis_id: str,
    service: MotionService = Depends(get_motion_service)
) -> MotionResponse:
    """Stop axis motion.
    
    Args:
        axis_id: Axis identifier
        
    Returns:
        Stop response
    """
    try:
        logger.debug(f"Stopping axis {axis_id}")
        await service.stop_axis(axis_id)
        
        return MotionResponse(
            status="ok",
            message=f"Stopped axis {axis_id}",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to stop axis {axis_id}: {str(e)}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to stop axis {axis_id}"
        )
