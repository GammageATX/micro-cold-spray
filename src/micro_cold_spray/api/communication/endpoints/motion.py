"""Motion control endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends

from ..models.motion import (
    SingleAxisMoveRequest, CoordinatedMoveRequest,
    MotionStatus
)
from ..service import CommunicationService
from ...base import get_service

router = APIRouter(prefix="/motion", tags=["motion"])


@router.get("/status")
async def get_motion_status(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> MotionStatus:
    """Get current motion status."""
    return await service.motion.get_status()


@router.post("/move")
async def move_axis(
    request: SingleAxisMoveRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Execute single axis move."""
    try:
        await service.motion.move_axis(
            request.axis,
            request.position,
            request.velocity
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/move/xy")
async def move_xy(
    request: CoordinatedMoveRequest,
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Execute coordinated XY move."""
    try:
        await service.motion.move_xy(
            request.x_position,
            request.y_position,
            request.velocity
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/home")
async def home_axes(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Home all axes."""
    try:
        await service.motion.home_axes()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/stop")
async def stop_motion(
    service: CommunicationService = Depends(get_service(CommunicationService))
) -> Dict[str, Any]:
    """Stop all motion."""
    try:
        await service.motion.stop_motion()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
